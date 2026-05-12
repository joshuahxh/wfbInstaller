// Side-rail Table of Contents:
//   1. Build links from every <h2> (and nested <h3>) under article.page that has an id.
//   2. Hide the duplicate in-page ToC (the "Table of Contents" heading + ordered list
//      that lives at the top of the markdown).
//   3. Highlight the link whose section the reader is currently looking at.
//   4. Auto-scroll the sidebar so the active link stays visible.
//   5. On narrow viewports, expose the sidebar as a top-drawer toggled from the header.

(function () {
  "use strict";

  const article = document.querySelector("article.page");
  const tocList = document.querySelector(".toc__list");
  const sidebar = document.querySelector(".toc");
  if (!article || !tocList || !sidebar) return;

  // ---- Hide the in-page ToC (it's redundant now). -------------------------
  hideInlineToc(article);

  // ---- Collect headings. --------------------------------------------------
  const sections = [];
  article.querySelectorAll("h2[id], h3[id]").forEach(function (h) {
    sections.push(h);
  });
  if (sections.length === 0) return;

  // ---- Build the sidebar list. --------------------------------------------
  sections.forEach(function (h) {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = "#" + h.id;
    a.textContent = h.textContent.replace(/\s+/g, " ").trim();
    a.className = "toc__link toc__link--" + h.tagName.toLowerCase();
    a.addEventListener("click", function () {
      // Close mobile drawer after picking a link.
      if (sidebar.hasAttribute("data-open")) {
        sidebar.removeAttribute("data-open");
        const toggle = document.querySelector(".site-header__menu-toggle");
        if (toggle) toggle.setAttribute("aria-expanded", "false");
      }
    });
    li.appendChild(a);
    tocList.appendChild(li);
  });

  sidebar.classList.add("toc--ready");
  const links = Array.from(tocList.querySelectorAll(".toc__link"));
  const tocInner = sidebar.querySelector(".toc__inner");

  // ---- Active-section tracking. -------------------------------------------
  // Use scroll position to find the heading nearest the top of the viewport.
  // This is more robust than IntersectionObserver when several sections are
  // visible at once (long viewport, short sections).
  let activeLink = null;
  let ticking = false;

  function updateActive() {
    ticking = false;
    const triggerY = window.scrollY + 110; // a bit below the sticky header
    let current = sections[0];
    for (let i = 0; i < sections.length; i++) {
      if (sections[i].offsetTop <= triggerY) current = sections[i];
      else break;
    }
    const nextLink = links.find(function (a) {
      return a.getAttribute("href") === "#" + current.id;
    });
    if (nextLink === activeLink) return;
    if (activeLink) activeLink.classList.remove("toc__link--active");
    if (nextLink) {
      nextLink.classList.add("toc__link--active");
      ensureVisible(nextLink, tocInner);
    }
    activeLink = nextLink;
  }

  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(updateActive);
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });
  updateActive();

  // ---- Mobile drawer toggle. ----------------------------------------------
  const toggle = document.querySelector(".site-header__menu-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      const open = sidebar.getAttribute("data-open") === "true";
      if (open) {
        sidebar.removeAttribute("data-open");
        toggle.setAttribute("aria-expanded", "false");
      } else {
        sidebar.setAttribute("data-open", "true");
        toggle.setAttribute("aria-expanded", "true");
      }
    });
  }

  // ---- Helpers. -----------------------------------------------------------
  function hideInlineToc(root) {
    // Find an <h2> whose text is "Table of Contents" and move it (plus the
    // following list and any separator <hr>, up to the next <h2>) into a
    // hidden wrapper.
    const headings = root.querySelectorAll("h2");
    for (let i = 0; i < headings.length; i++) {
      const h = headings[i];
      if (h.textContent.trim().toLowerCase() !== "table of contents") continue;

      const parent = h.parentNode;
      const wrap = document.createElement("div");
      wrap.className = "page__inline-toc";
      wrap.hidden = true;

      // Collect h + every following sibling until (but not including) the next <h2>.
      const nodes = [h];
      let n = h.nextElementSibling;
      while (n && n.tagName !== "H2") {
        nodes.push(n);
        n = n.nextElementSibling;
      }

      // Insert the wrapper where h used to be, then move the collected nodes into it.
      parent.insertBefore(wrap, h);
      nodes.forEach(function (el) { wrap.appendChild(el); });
      return;
    }
  }

  function ensureVisible(el, container) {
    if (!container) return;
    const cTop = container.scrollTop;
    const cBottom = cTop + container.clientHeight;
    const elTop = el.offsetTop;
    const elBottom = elTop + el.offsetHeight;
    if (elTop < cTop + 8) {
      container.scrollTop = Math.max(0, elTop - 12);
    } else if (elBottom > cBottom - 8) {
      container.scrollTop = elBottom - container.clientHeight + 12;
    }
  }
})();
