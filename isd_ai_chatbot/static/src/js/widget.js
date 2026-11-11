/*
 * AI Chatbot widget (isd_ai_chatbot).
 *
 * One file for Odoo's own pages and for any outside site:
 *   <script src="https://your-odoo/isd_ai_chatbot/widget.js" defer></script>
 *
 * It works out the Odoo address from its own <script> tag, so the same tag
 * works whatever domain it is pasted into. Plain ES5 and no dependencies:
 * it has to run on sites we know nothing about.
 */
(function () {
  "use strict";
  if (window.__isdAiChatbotLoaded) return;
  window.__isdAiChatbotLoaded = true;

  var script = document.currentScript || (function () {
    var tags = document.getElementsByTagName("script");
    for (var i = tags.length - 1; i >= 0; i--) {
      if ((tags[i].src || "").indexOf("/isd_ai_chatbot/widget.js") !== -1) return tags[i];
    }
    return null;
  })();
  var BASE = script && script.src ? script.src.split("/isd_ai_chatbot/")[0] : "";
  var SID_KEY = "isd_ai_chatbot_sid";
  var LANG_KEY = "isd_ai_chatbot_lang";

  var L = {
    vi: {
      placeholder: "Nhập câu hỏi của bạn...", send: "Gửi", thinking: "Đang trả lời...",
      handoff: "Nói chuyện với người thật", handoffMsg: "Mình muốn nói chuyện với người thật.",
      disclaimer: "Trợ lý AI · có thể sai sót, hãy kiểm tra thông tin quan trọng",
      reset: "Cuộc trò chuyện mới", close: "Đóng", formTitle: "Để lại thông tin, chúng tôi gọi lại ngay",
      name: "Họ và tên *", phone: "Số điện thoại", email: "Email", topic: "Bạn cần tư vấn gì?",
      when: "Thời gian mong muốn (không bắt buộc)", submit: "Gửi thông tin",
      needContact: "Vui lòng nhập họ tên và số điện thoại hoặc email.",
      thanks: "✅ Cảm ơn **{name}**! Chúng tôi đã nhận thông tin và sẽ liên hệ lại sớm nhất.",
      error: "Xin lỗi, kết nối đang gián đoạn. Bạn bấm **Nói chuyện với người thật** bên dưới nhé!",
      chat: "Chat", call: "Gọi điện", zalo: "Zalo", messenger: "Messenger", source: "Nguồn",
    },
    en: {
      placeholder: "Type your question...", send: "Send", thinking: "Typing...",
      handoff: "Talk to a person", handoffMsg: "I'd like to talk to a real person.",
      disclaimer: "AI assistant · may make mistakes, please check important details",
      reset: "New conversation", close: "Close", formTitle: "Leave your details and we'll call you back",
      name: "Full name *", phone: "Phone number", email: "Email", topic: "What can we help with?",
      when: "Preferred time (optional)", submit: "Send details",
      needContact: "Please enter your name and a phone number or email.",
      thanks: "✅ Thank you, **{name}**! We have your details and will be in touch shortly.",
      error: "Sorry, the connection dropped. Tap **Talk to a person** below.",
      chat: "Chat", call: "Call", zalo: "Zalo", messenger: "Messenger", source: "Source",
    },
  };

  var ICONS = {
    toggle: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    close: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
    chat: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    phone: '<svg width="22" height="22" viewBox="0 0 24 24" fill="#fff"><path d="M6.6 10.8c1.4 2.8 3.8 5.1 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1-9.4 0-17-7.6-17-17 0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.3 0 .7-.2 1L6.6 10.8z"/></svg>',
    zalo: '<svg width="24" height="24" viewBox="0 0 48 48"><text x="50%" y="62%" text-anchor="middle" font-size="22" font-family="Arial" font-weight="700" fill="#fff">Zalo</text></svg>',
    messenger: '<svg width="22" height="22" viewBox="0 0 24 24" fill="#fff"><path d="M12 2C6.48 2 2 6.15 2 11.26c0 2.91 1.45 5.51 3.73 7.21V22l3.4-1.87c.91.25 1.87.39 2.87.39 5.52 0 10-4.15 10-9.26C22 6.15 17.52 2 12 2zm1.01 12.47l-2.55-2.72-4.98 2.72 5.47-5.81 2.61 2.72 4.91-2.72-5.46 5.81z"/></svg>',
  };

  function store(key, value) {
    try {
      if (value === undefined) return window.localStorage.getItem(key);
      window.localStorage.setItem(key, value);
    } catch (e) { /* private mode: work without remembering */ }
    return null;
  }

  function newSessionId() {
    var hex = "";
    for (var i = 0; i < 32; i++) hex += Math.floor(Math.random() * 16).toString(16);
    return hex;
  }

  function esc(str) {
    return String(str == null ? "" : str)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  // Escape first, then add the little formatting the bot uses. Nothing the
  // server sends is ever inserted as raw HTML.
  function format(str) {
    return esc(str)
      .replace(/^(?:\*|-|•)\s+(.*)$/gm, "• $1")
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\[(\d+)\]/g, '<button type="button" class="isdc-cite" data-cite="$1">[$1]</button>')
      .replace(/\n/g, "<br/>");
  }

  function safeUrl(url) {
    var s = String(url || "").trim();
    return /^(https?:\/\/|tel:|\/)/i.test(s) ? s : "";
  }

  function post(path, body) {
    return fetch(BASE + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(function (r) {
      return r.json().then(function (data) { data._status = r.status; return data; });
    });
  }

  function detectLang() {
    var saved = store(LANG_KEY);
    if (saved === "vi" || saved === "en") return saved;
    var page = (document.documentElement.lang || navigator.language || "vi").toLowerCase();
    return page.indexOf("en") === 0 ? "en" : "vi";
  }

  function el(tag, cls, html) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (html != null) node.innerHTML = html;
    return node;
  }

  function mount(cfg) {
    var lang = detectLang();
    var sid = store(SID_KEY) || newSessionId();
    store(SID_KEY, sid);
    var buttons = cfg.buttons || {};
    var colors = cfg.colors || {};
    var icons = cfg.icons || {};
    var lastCitations = [];
    var isOpen = false;

    function t(key) { return (L[lang] || L.vi)[key]; }
    function icon(name) {
      var url = safeUrl(icons[name]);
      return url ? '<img src="' + esc(url) + '" alt="" class="isdc-fab-img"/>' : ICONS[name];
    }
    function avatar(cls) {
      var url = safeUrl(cfg.avatarUrl);
      var letter = esc(String(cfg.botTitle || "A").trim().charAt(0).toUpperCase());
      return url ? '<img src="' + esc(url) + '" class="' + cls + '" alt=""/>'
                 : '<div class="' + cls + '">' + letter + "</div>";
    }

    var root = el("div");
    root.id = "isdc-root";
    root.style.setProperty("--isdc-primary", cfg.primaryColor || "#0b53cb");
    root.style.setProperty("--isdc-secondary", cfg.secondaryColor || "#1d4ed8");

    // ---- launcher: one round button that opens a column of contact buttons
    var contacts = [];
    if (safeUrl(buttons.messenger)) contacts.push({ key: "messenger", href: buttons.messenger });
    if (safeUrl(buttons.zalo)) contacts.push({ key: "zalo", href: buttons.zalo });
    if (buttons.phone) contacts.push({ key: "phone", href: "tel:" + String(buttons.phone).replace(/[^\d+]/g, "") });
    var hasChat = buttons.chat !== false;

    var fabList = el("div", "isdc-fab-list");
    contacts.forEach(function (c) {
      var a = el("a", "isdc-fab", icon(c.key));
      a.href = c.href;
      if (c.key !== "phone") { a.target = "_blank"; a.rel = "noopener"; }
      a.title = t(c.key === "phone" ? "call" : c.key);
      a.style.background = colors[c.key] || "#0b53cb";
      fabList.appendChild(a);
    });
    var chatFab = null;
    if (hasChat) {
      chatFab = el("button", "isdc-fab", icon("chat"));
      chatFab.type = "button";
      chatFab.title = t("chat");
      chatFab.style.background = colors.chat || cfg.primaryColor || "#0b53cb";
      fabList.appendChild(chatFab);
    }
    // With only the chat there is nothing to fan out: the main button opens it
    var direct = contacts.length === 0;
    var toggle = el("button", "isdc-fab isdc-toggle", icon("toggle"));
    toggle.type = "button";
    toggle.setAttribute("aria-label", cfg.botTitle || "Chat");
    toggle.style.background = colors.toggle || cfg.primaryColor || "#0b53cb";

    var callout = el("div", "isdc-callout");

    // ---- chat window
    var win = el("div", "isdc-window");
    win.innerHTML =
      '<div class="isdc-header">' +
      '  <div class="isdc-head-left">' + avatar("isdc-head-avatar") +
      '    <div class="isdc-head-text"><div class="isdc-title">' + esc(cfg.botTitle || "") + "</div>" +
      '    <div class="isdc-sub">' + esc(cfg.botSubtitle || "") + "</div></div></div>" +
      '  <div class="isdc-head-actions">' +
      '    <button type="button" class="isdc-icon-btn isdc-lang"></button>' +
      '    <button type="button" class="isdc-icon-btn isdc-reset">↻</button>' +
      '    <button type="button" class="isdc-icon-btn isdc-close">✕</button>' +
      "  </div>" +
      "</div>" +
      '<form class="isdc-form" novalidate>' +
      '  <div class="isdc-form-head"><strong class="isdc-form-title"></strong><span class="isdc-form-x">✕</span></div>' +
      '  <input class="isdc-f-name" autocomplete="name"/>' +
      '  <div class="isdc-row"><input class="isdc-f-phone" autocomplete="tel"/><input class="isdc-f-email" type="email" autocomplete="email"/></div>' +
      '  <input class="isdc-f-topic"/>' +
      '  <label class="isdc-f-when-label"></label><input class="isdc-f-when" type="datetime-local"/>' +
      '  <div class="isdc-form-err"></div>' +
      '  <button type="submit" class="isdc-f-submit"></button>' +
      "</form>" +
      '<div class="isdc-msgs"></div>' +
      '<div class="isdc-cite-drawer"></div>' +
      '<div class="isdc-footer">' +
      '  <form class="isdc-input-row"><input class="isdc-input" maxlength="1000"/><button type="submit" class="isdc-send"></button></form>' +
      '  <div class="isdc-disclaimer"><span class="isdc-disc-text"></span>' +
      '  <button type="button" class="isdc-handoff"></button></div>' +
      "</div>";

    root.appendChild(win);
    root.appendChild(callout);
    if (!direct) root.appendChild(fabList);
    root.appendChild(toggle);
    document.body.appendChild(root);

    function $(sel) { return win.querySelector(sel); }
    var msgs = $(".isdc-msgs"), drawer = $(".isdc-cite-drawer"), form = $(".isdc-form");
    var input = $(".isdc-input"), formErr = $(".isdc-form-err");

    function applyLang() {
      $(".isdc-lang").textContent = lang === "vi" ? "EN" : "VI";
      $(".isdc-lang").title = lang === "vi" ? "English" : "Tiếng Việt";
      $(".isdc-reset").title = t("reset");
      $(".isdc-close").title = t("close");
      input.placeholder = t("placeholder");
      $(".isdc-send").textContent = t("send");
      $(".isdc-disc-text").textContent = t("disclaimer") + " · ";
      $(".isdc-handoff").textContent = t("handoff");
      $(".isdc-form-title").textContent = t("formTitle");
      $(".isdc-f-name").placeholder = t("name");
      $(".isdc-f-phone").placeholder = t("phone");
      $(".isdc-f-email").placeholder = t("email");
      $(".isdc-f-topic").placeholder = t("topic");
      $(".isdc-f-when-label").textContent = t("when");
      $(".isdc-f-submit").textContent = t("submit");
      var greeting = (cfg.greeting || {})[lang] || "";
      callout.innerHTML = greeting ? "<strong>" + esc(cfg.botTitle || "") + "</strong><span>" + esc(greeting) + "</span>" : "";
      callout.style.display = greeting && !isOpen && !store("isd_ai_chatbot_callout_seen") ? "block" : "none";
    }

    function addMessage(role, text) {
      var row = el("div", role === "user" ? "isdc-row-user" : "isdc-row-bot");
      var bubble = el("div", "isdc-msg isdc-" + role, format(text));
      if (role !== "user") row.appendChild(el("div", null, avatar("isdc-msg-avatar")).firstChild);
      row.appendChild(bubble);
      msgs.appendChild(row);
      msgs.scrollTop = msgs.scrollHeight;
      return bubble;
    }

    function welcome() {
      msgs.innerHTML = "";
      addMessage("bot", (cfg.welcome || {})[lang] || "");
      var list = (cfg.suggested || {})[lang] || [];
      if (!list.length) return;
      var wrap = el("div", "isdc-suggestions");
      list.forEach(function (q) {
        var b = el("button", "isdc-pill");
        b.type = "button";
        b.textContent = q;
        b.onclick = function () { send(q); };
        wrap.appendChild(b);
      });
      msgs.appendChild(wrap);
    }

    function setOpen(open) {
      isOpen = open;
      win.className = open ? "isdc-window isdc-open" : "isdc-window";
      if (open) {
        callout.style.display = "none";
        store("isd_ai_chatbot_callout_seen", "1");
        setTimeout(function () { input.focus(); }, 50);
      }
    }

    var expanded = false;
    toggle.onclick = function () {
      if (direct) { setOpen(!isOpen); toggle.innerHTML = isOpen ? ICONS.close : icon("toggle"); return; }
      expanded = !expanded;
      fabList.className = expanded ? "isdc-fab-list isdc-fab-open" : "isdc-fab-list";
      toggle.innerHTML = expanded ? ICONS.close : icon("toggle");
      if (!expanded) setOpen(false);
    };
    if (chatFab) chatFab.onclick = function () { setOpen(!isOpen); };
    callout.onclick = function () {
      setOpen(true);
      if (direct) toggle.innerHTML = ICONS.close;
    };
    $(".isdc-close").onclick = function () {
      setOpen(false);
      if (direct) toggle.innerHTML = icon("toggle");
    };
    $(".isdc-reset").onclick = function () {
      sid = newSessionId();
      store(SID_KEY, sid);
      drawer.style.display = "none";
      form.style.display = "none";
      welcome();
    };
    $(".isdc-lang").onclick = function () {
      lang = lang === "vi" ? "en" : "vi";
      store(LANG_KEY, lang);
      applyLang();
      welcome();
    };
    $(".isdc-handoff").onclick = function () { send(t("handoffMsg")); };
    $(".isdc-form-x").onclick = function () { form.style.display = "none"; };

    msgs.onclick = function (e) {
      var target = e.target;
      if (!target || !target.classList || !target.classList.contains("isdc-cite")) return;
      var idx = parseInt(target.getAttribute("data-cite") || "1", 10);
      var c = lastCitations[idx - 1];
      if (!c) return;
      drawer.innerHTML = '<div class="isdc-drawer-head"><span>[' + esc(c.index) + "] " + esc(c.title) +
        '</span><span class="isdc-drawer-x">✕</span></div><div class="isdc-drawer-sub">' + esc(c.sectionHeading) +
        "</div><div>" + esc(c.snippet) + "</div>";
      drawer.style.display = "block";
      drawer.querySelector(".isdc-drawer-x").onclick = function () { drawer.style.display = "none"; };
    };

    function send(text) {
      var q = String(text || "").trim();
      if (!q) return;
      var sug = msgs.querySelector(".isdc-suggestions");
      if (sug) sug.parentNode.removeChild(sug);
      addMessage("user", q);
      input.value = "";
      var pending = addMessage("bot", t("thinking"));
      post("/isd_ai_chatbot/api/chat", { message: q, session_id: sid, lang: lang, page_url: location.href })
        .then(function (data) {
          if (!data.ok) throw new Error(data.error || "error");
          if (data.sessionId) { sid = data.sessionId; store(SID_KEY, sid); }
          lastCitations = data.citations || [];
          pending.innerHTML = format(data.reply || t("error"));
          if (data.showLeadForm && !data.leadCaptured) form.style.display = "flex";
          if (data.leadCaptured) form.style.display = "none";
          msgs.scrollTop = msgs.scrollHeight;
        })
        .catch(function () { pending.innerHTML = format(t("error")); });
    }

    $(".isdc-input-row").onsubmit = function (e) { e.preventDefault(); send(input.value); };

    form.onsubmit = function (e) {
      e.preventDefault();
      var name = $(".isdc-f-name").value.trim();
      var phone = $(".isdc-f-phone").value.trim();
      var email = $(".isdc-f-email").value.trim();
      if (!name || !(phone || email)) { formErr.textContent = t("needContact"); return; }
      formErr.textContent = "";
      post("/isd_ai_chatbot/api/lead", {
        name: name, phone: phone, email: email, session_id: sid,
        message: $(".isdc-f-topic").value.trim(), datetime: $(".isdc-f-when").value,
      }).then(function (data) {
        if (!data.ok) { formErr.textContent = data.error || t("needContact"); return; }
        form.reset();
        form.style.display = "none";
        addMessage("bot", t("thanks").replace("{name}", name));
      }).catch(function () { formErr.textContent = t("error"); });
    };

    applyLang();
    welcome();
  }

  function start() {
    if (!BASE) return;
    var css = document.createElement("link");
    css.rel = "stylesheet";
    css.href = BASE + "/isd_ai_chatbot/widget.css";
    document.head.appendChild(css);
    fetch(BASE + "/isd_ai_chatbot/api/config")
      .then(function (r) { return r.json(); })
      .then(mount)
      .catch(function () { /* the server is unreachable: show nothing rather than a broken bubble */ });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
