const LANGUAGES = [
  { code: "en", name: "English" },
  { code: "hi", name: "हिन्दी (Hindi)" },
  { code: "bn", name: "বাংলা (Bengali)" },
  { code: "te", name: "తెలుగు (Telugu)" },
  { code: "mr", name: "मराठी (Marathi)" },
  { code: "ta", name: "தமிழ் (Tamil)" },
  { code: "ur", name: "اردو (Urdu)" },
  { code: "gu", name: "ગુજરાતી (Gujarati)" },
  { code: "kn", name: "ಕನ್ನಡ (Kannada)" },
  { code: "ml", name: "മലയാളം (Malayalam)" },
  { code: "pa", name: "ਪੰਜਾਬੀ (Punjabi)" },
  { code: "or", name: "ଓଡ଼ିଆ (Odia)" },
  { code: "as", name: "অসমীয়া (Assamese)" },
  { code: "kok", name: "कोंकणी (Konkani)" },
  { code: "mai", name: "मैथिली (Maithili)" },
  { code: "mni", name: "মৈতৈলোন্ (Manipuri)" },
  { code: "sat", name: "ᱥᱟᱱᱛᱟᱲᱤ (Santali)" },
  { code: "ks", name: "कॉशुर (Kashmiri)" },
  { code: "doi", name: "डोगरी (Dogri)" },
  { code: "bodo", name: "बर' (Bodo)" },
  { code: "ne", name: "नेपाली (Nepali)" },
  { code: "sd", name: "सिन्धी (Sindhi)" },
];

function triggerGoogleTranslate(langCode) {
  try {
    const googleSelect = document.querySelector(".goog-te-combo");
    if (googleSelect) {
      googleSelect.value = langCode;
      googleSelect.dispatchEvent(new Event("change"));
    } else {
      console.warn(
        "Google Translate select element not found - check if the widget has loaded."
      );
    }
  } catch (e) {
    console.error("Error triggering Google Translate:", e);
  }
}

function updateLanguageDisplay(langName) {
  const displayName = langName.split("(")[0].trim();

  const spans = [
    document.getElementById("desktop-current-lang"),
    document.getElementById("mobile-current-lang"),
    document.getElementById("current_lang"),
  ];

  spans.forEach((span) => {
    if (span) span.textContent = displayName;
  });
}

function setupDropdown(selectorId) {
  const selector = document.getElementById(selectorId);
  if (!selector) return;

  const button = selector.querySelector("button");
  const dropdown = selector.querySelector('div[id$="-dropdown"]');
  const langLinks = dropdown.querySelectorAll("a");

  button.addEventListener("click", (event) => {
    event.stopPropagation();
    dropdown.classList.toggle("hidden");
  });

  langLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      const selectedLangName = link.textContent.trim();
      const selectedLangCode = link.getAttribute("data-lang");

      updateLanguageDisplay(selectedLangName);
      forceTranslate(selectedLangCode);

      dropdown.classList.add("hidden");
    });
  });

  window.addEventListener("click", (event) => {
    if (!selector.contains(event.target)) {
      dropdown.classList.add("hidden");
    }
  });
}

function populateLanguageLists() {
  const desktopList = document.getElementById("desktop-lang-list");
  const mobileList = document.getElementById("mobile-lang-list");
  const baseList = document.getElementById("base-lang-list");

  if (desktopList) desktopList.innerHTML = "";
  if (mobileList) mobileList.innerHTML = "";
  if (baseList) baseList.innerHTML = "";

  LANGUAGES.forEach((lang) => {
    const desktopHtml = `<a href="#" data-lang="${lang.code}" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">${lang.name}</a>`;

    if (desktopList) desktopList.innerHTML += desktopHtml;
    if (mobileList)
      mobileList.innerHTML += `<a href="#" data-lang="${lang.code}" class="block p-2 text-sm text-gray-700 hover:bg-gray-100 rounded">${lang.name}</a>`;
    if (baseList) baseList.innerHTML += desktopHtml;
  });
}

function setupLanguageDropdowns() {
  populateLanguageLists();
  setupDropdown("desktop-lang-selector");
  setupDropdown("mobile-lang-selector");
  setupDropdown("base-lang-selector");
}

document.addEventListener("DOMContentLoaded", setupLanguageDropdowns);

function googleTranslateElementInit() {
  const includedLanguages = LANGUAGES.map((lang) => lang.code).join(",");

  new google.translate.TranslateElement(
    {
      pageLanguage: "en",
      includedLanguages: includedLanguages,
      layout: google.translate.TranslateElement.InlineLayout.HORIZONTAL,
      autoDisplay: false,
    },
    "google_translate_element"
  );
}

(function () {
  var script = document.createElement("script");
  script.src =
    "https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit";
  document.head.appendChild(script);
})();

function resetGoogleTranslate() {
  const googleSelect = document.querySelector(".goog-te-combo");
  if (googleSelect) {
    googleSelect.value = "en";
    googleSelect.dispatchEvent(new Event("change"));
  }
}

function forceTranslate(langCode) {
  const googleSelect = document.querySelector(".goog-te-combo");
  if (googleSelect) {
    if (langCode === "en") {
      if (googleSelect.value !== "en") {
        resetGoogleTranslate();
        setTimeout(() => {
          triggerGoogleTranslate(langCode);
        }, 500);
      } else {
        triggerGoogleTranslate(langCode);
      }
    } else {
      triggerGoogleTranslate(langCode);
    }
  }
}
