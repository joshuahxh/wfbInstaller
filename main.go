package main

import (
	"archive/zip"
	"bufio"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	neturl "net/url"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

const usageText = `To install a Garmin app on your device, drag and drop a downloaded ZIP file,
an extracted PRG file, or pass a Watchface Builder URL:

  wfbinstaller path/to/file.zip
  wfbinstaller path/to/file.prg
  wfbinstaller https://garmin.watchfacebuilder.com/watchface/xxxxx/
`

type app struct {
	logger *log.Logger
	reader *bufio.Reader
	out    io.Writer
}

type cleanupStack struct {
	funcs []func()
}

type installTarget struct {
	SourcePath       string
	AppName          string
	Extension        string
	DesiredFileName  string
	DisplayFileName  string
	DisplaySourceRef string
}

func main() {
	application := &app{
		logger: log.New(os.Stdout, "", 0),
		reader: bufio.NewReader(os.Stdin),
		out:    os.Stdout,
	}

	if err := application.run(os.Args[1:]); err != nil {
		application.logger.Printf("Error: %v", err)
		os.Exit(1)
	}
}

func (a *app) run(args []string) error {
	device, err := a.selectDeviceLoop()
	if err != nil {
		return err
	}

	input, err := a.readSource(args)
	if err != nil {
		return err
	}

	if input == "" {
		a.printUsage()
		return nil
	}

	targets, cleanup, err := a.prepareTargets(input)
	if cleanup != nil {
		defer cleanup()
	}
	if err != nil {
		return err
	}

	if len(targets) > 1 {
		a.logger.Printf("Found %d installable files.", len(targets))
	}

	if err := a.uploadTargets(*device, targets); err != nil {
		return err
	}

	a.logger.Println("Done.")
	return nil
}

func (a *app) selectDeviceLoop() (*deviceInfo, error) {
	for {
		devices := a.discoverDevices()

		if len(devices) == 0 {
			a.logger.Println("No Garmin device found. Press Enter to refresh or Ctrl+C to exit.")
			if _, err := a.promptLine(""); err != nil {
				if errors.Is(err, io.EOF) {
					return nil, errors.New("no Garmin device found")
				}
				return nil, err
			}
			continue
		}

		if len(devices) == 1 {
			device := devices[0]
			a.logger.Printf("Auto-selected device: %s", device.Name)
			return &device, nil
		}

		a.logger.Println("Available devices:")
		for _, device := range devices {
			a.logger.Printf("%d: %s [%s]", device.Index, device.Name, device.Transport)
		}

		selection, err := a.promptLine("Enter the number to select a device, or press Enter to refresh: ")
		if err != nil {
			if errors.Is(err, io.EOF) {
				return nil, errors.New("device selection cancelled")
			}
			return nil, err
		}

		if selection == "" {
			continue
		}

		index, err := strconv.Atoi(selection)
		if err != nil || index < 1 || index > len(devices) {
			a.logger.Printf("Invalid device selection: %q", selection)
			continue
		}

		device := devices[index-1]
		a.logger.Printf("Selected device: %s", device.Name)
		return &device, nil
	}
}

func (a *app) readSource(args []string) (string, error) {
	if len(args) > 0 {
		return normalizeUserInput(args[0]), nil
	}

	input, err := a.promptLine("Type or drag a URL, ZIP file, PRG file, or SET file here, then press Enter: ")
	if err != nil {
		if errors.Is(err, io.EOF) {
			return "", nil
		}
		return "", err
	}

	return input, nil
}

func (a *app) printUsage() {
	fmt.Fprint(a.out, usageText)
}

func (a *app) promptLine(prompt string) (string, error) {
	if prompt != "" {
		fmt.Fprint(a.out, prompt)
	}

	line, err := a.reader.ReadString('\n')
	if err != nil {
		if errors.Is(err, io.EOF) {
			line = strings.TrimSpace(line)
			if line == "" {
				return "", io.EOF
			}
			return normalizeUserInput(line), nil
		}
		return "", err
	}

	return normalizeUserInput(line), nil
}

func normalizeUserInput(input string) string {
	trimmed := strings.TrimSpace(input)
	if len(trimmed) >= 2 {
		if (trimmed[0] == '"' && trimmed[len(trimmed)-1] == '"') || (trimmed[0] == '\'' && trimmed[len(trimmed)-1] == '\'') {
			trimmed = trimmed[1 : len(trimmed)-1]
		}
	}
	return strings.TrimSpace(trimmed)
}

func (a *app) prepareTargets(input string) ([]installTarget, func(), error) {
	input = normalizeUserInput(input)

	cleanups := &cleanupStack{}
	if strings.HasPrefix(strings.ToLower(input), "http://") || strings.HasPrefix(strings.ToLower(input), "https://") {
		downloaded, cleanup, err := a.downloadRelease(input)
		if err != nil {
			return nil, nil, err
		}
		cleanups.Add(cleanup)
		input = downloaded
	}

	if _, err := os.Stat(input); err != nil {
		return nil, cleanups.Run, fmt.Errorf("input not found: %s", input)
	}

	ext := strings.ToLower(filepath.Ext(input))
	switch ext {
	case ".zip":
		targets, cleanup, err := a.extractTargetsFromZip(input)
		if err != nil {
			cleanups.Run()
			return nil, nil, err
		}
		cleanups.Add(cleanup)
		return targets, cleanups.Run, nil
	case ".prg", ".set":
		return []installTarget{newInstallTarget(input)}, cleanups.Run, nil
	default:
		cleanups.Run()
		return nil, nil, fmt.Errorf("unsupported input type: %s", ext)
	}
}

func (a *app) downloadRelease(rawURL string) (string, func(), error) {
	downloadURL, err := ensureFileQuery(rawURL)
	if err != nil {
		return "", nil, err
	}

	a.logger.Printf("Downloading %s...", downloadURL)
	client := &http.Client{Timeout: 2 * time.Minute}
	response, err := client.Get(downloadURL)
	if err != nil {
		return "", nil, fmt.Errorf("download failed: %w", err)
	}
	defer response.Body.Close()

	if response.StatusCode != http.StatusOK {
		return "", nil, fmt.Errorf("download failed: unexpected status %s", response.Status)
	}

	file, err := os.CreateTemp("", "wfbinstaller_*.zip")
	if err != nil {
		return "", nil, err
	}

	if _, err := io.Copy(file, response.Body); err != nil {
		file.Close()
		os.Remove(file.Name())
		return "", nil, fmt.Errorf("download failed: %w", err)
	}

	if err := file.Close(); err != nil {
		os.Remove(file.Name())
		return "", nil, err
	}

	cleanup := func() {
		_ = os.Remove(file.Name())
	}

	return file.Name(), cleanup, nil
}

func ensureFileQuery(rawURL string) (string, error) {
	parsed, err := neturl.Parse(rawURL)
	if err != nil {
		return "", fmt.Errorf("invalid URL: %w", err)
	}

	query := parsed.Query()
	if query.Get("file") != "app" {
		query.Set("file", "app")
		parsed.RawQuery = query.Encode()
	}

	return parsed.String(), nil
}

func (a *app) extractTargetsFromZip(zipPath string) ([]installTarget, func(), error) {
	reader, err := zip.OpenReader(zipPath)
	if err != nil {
		return nil, nil, fmt.Errorf("invalid zip file: %w", err)
	}
	defer reader.Close()

	tempDir, err := os.MkdirTemp("", "wfbinstaller_zip_*")
	if err != nil {
		return nil, nil, err
	}

	cleanup := func() {
		_ = os.RemoveAll(tempDir)
	}

	targets := make([]installTarget, 0)
	for _, file := range reader.File {
		if file.FileInfo().IsDir() {
			continue
		}

		ext := strings.ToLower(filepath.Ext(file.Name))
		if ext != ".prg" && ext != ".set" {
			continue
		}

		baseName := filepath.Base(file.Name)
		if baseName == "." || baseName == string(filepath.Separator) || baseName == "" {
			continue
		}

		destination := filepath.Join(tempDir, baseName)
		if err := extractZipEntry(file, destination); err != nil {
			cleanup()
			return nil, nil, err
		}

		targets = append(targets, newInstallTarget(destination))
	}

	if len(targets) == 0 {
		cleanup()
		return nil, nil, errors.New("zip file does not contain any .prg or .set payloads")
	}

	sort.Slice(targets, func(i, j int) bool {
		return strings.ToLower(targets[i].DesiredFileName) < strings.ToLower(targets[j].DesiredFileName)
	})

	return targets, cleanup, nil
}

func extractZipEntry(file *zip.File, destination string) error {
	reader, err := file.Open()
	if err != nil {
		return err
	}
	defer reader.Close()

	out, err := os.Create(destination)
	if err != nil {
		return err
	}

	if _, err := io.Copy(out, reader); err != nil {
		out.Close()
		return err
	}

	return out.Close()
}

func newInstallTarget(sourcePath string) installTarget {
	ext := strings.ToLower(filepath.Ext(sourcePath))
	baseName := strings.TrimSuffix(filepath.Base(sourcePath), filepath.Ext(sourcePath))
	desiredExt := ".prg"
	if ext == ".set" {
		desiredExt = ".SET"
	}

	desiredName := baseName + desiredExt
	return installTarget{
		SourcePath:       sourcePath,
		AppName:          baseName,
		Extension:        ext,
		DesiredFileName:  desiredName,
		DisplayFileName:  desiredName,
		DisplaySourceRef: sourcePath,
	}
}

func (t installTarget) filesystemRelativeSegments() []string {
	if t.Extension == ".set" {
		return []string{"Apps", "Settings", t.DesiredFileName}
	}
	return []string{"Apps", t.DesiredFileName}
}

func (t installTarget) filesystemDestination(garminRoot string) string {
	parts := append([]string{garminRoot}, t.filesystemRelativeSegments()...)
	return filepath.Join(parts...)
}

func (t installTarget) mtpDestinationDir() string {
	if t.Extension == ".set" {
		return "/GARMIN/Apps/Settings"
	}
	return "/GARMIN/Apps"
}

func (c *cleanupStack) Add(fn func()) {
	if fn != nil {
		c.funcs = append(c.funcs, fn)
	}
}

func (c *cleanupStack) Run() {
	for index := len(c.funcs) - 1; index >= 0; index-- {
		c.funcs[index]()
	}
	c.funcs = nil
}