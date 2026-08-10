console.log("Initializing location selects...");

(function () {
  if (window.LyraLocationSelects && typeof window.LyraLocationSelects.init === "function") {
    window.LyraLocationSelects.init(document);
    return;
  }

  function fallbackEndpoint(endpoint) {
    const match = window.location.pathname.match(/^\/([^/]+)\//);
    const firstSegment = match ? match[1].toLowerCase() : "";
    const appSegments = [
      "activity_log", "allowances", "bank", "brand", "category", "chart_of_accounts",
      "company", "crm", "customer", "expenses", "hr", "items", "payroll", "purchase",
      "sales", "tax", "user", "warehouse", "website"
    ];
    const prefix = firstSegment && !appSegments.includes(firstSegment) ? "/" + match[1] : "";
    return prefix + "/company/setup/" + endpoint + "/";
  }

  function getConfig() {
    const root = document.querySelector("[data-location-load-states-url]");
    const countriesUrl = root ? root.getAttribute("data-location-load-countries-url") : "";
    const statesUrl = root ? root.getAttribute("data-location-load-states-url") : "";
    const citiesUrl = root ? root.getAttribute("data-location-load-cities-url") : "";
    return {
      countriesUrl: countriesUrl && !countriesUrl.startsWith("#") ? countriesUrl : fallbackEndpoint("load-countries"),
      statesUrl: statesUrl && !statesUrl.startsWith("#") ? statesUrl : fallbackEndpoint("load-states"),
      citiesUrl: citiesUrl && !citiesUrl.startsWith("#") ? citiesUrl : fallbackEndpoint("load-cities"),
    };
  }

  function getOptionStateId(select) {
    const option = select.options[select.selectedIndex];
    return option ? option.getAttribute("data-location-id") || option.value : "";
  }

  function getRelatedField(select, id) {
    if (!id) return null;
    const form = select.closest("form");
    if (form) {
      const local = form.querySelector('[id="' + id + '"]');
      if (local) return local;
    }
    return document.getElementById(id);
  }

  function clearSelect(select, placeholder) {
    if (!select) return;
    select.innerHTML = "";
    const option = document.createElement("option");
    option.value = "";
    option.textContent = placeholder;
    select.appendChild(option);
  }

  function appendOption(select, value, text, locationId) {
    const option = document.createElement("option");
    option.value = value || "";
    option.textContent = text || value || "";
    if (locationId) option.setAttribute("data-location-id", locationId);
    select.appendChild(option);
  }

  function setSelectValue(select, value) {
    if (!select) return;
    const normalized = value || "";
    if (normalized && !Array.from(select.options).some((option) => option.value === normalized)) {
      appendOption(select, normalized, normalized);
    }
    select.value = normalized;
    if (normalized) select.setAttribute("data-current-value", normalized);
  }

  function triggerChange(select) {
    select.dispatchEvent(new Event("change", { bubbles: true }));
    if (window.jQuery && window.jQuery.fn && window.jQuery.fn.select2) {
      window.jQuery(select).trigger("change");
    }
  }

  function triggerSelect2Refresh(select) {
    if (window.jQuery && window.jQuery.fn && window.jQuery.fn.select2) {
      window.jQuery(select).trigger("change.select2");
    }
  }

  function enhanceSelect2(select, placeholder) {
    if (!select || !window.jQuery || !window.jQuery.fn || !window.jQuery.fn.select2) return;
    const $select = window.jQuery(select);
    if ($select.hasClass("select2-hidden-accessible")) return;
    const modal = $select.closest(".modal");
    $select.select2({
      placeholder: placeholder || select.getAttribute("data-placeholder") || "Select",
      allowClear: true,
      width: "100%",
      dropdownParent: modal.length ? modal : window.jQuery(document.body),
    });
  }

  function fetchJson(url) {
    return fetch(url, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    }).then((response) => {
      if (!response.ok) throw new Error("Location request failed: " + response.status);
      return response.json();
    });
  }

  function loadCountries(countrySelect) {
    const config = getConfig();
    const currentValue = countrySelect.getAttribute("data-current-value") || countrySelect.value;

    clearSelect(countrySelect, "Select Country");
    if (!config) {
      triggerSelect2Refresh(countrySelect);
      return Promise.resolve();
    }

    return fetchJson(config.countriesUrl)
      .then((data) => {
        (data.countries || []).forEach((country) => {
          appendOption(countrySelect, country.code, country.name);
        });
        if (currentValue) setSelectValue(countrySelect, currentValue);
        triggerSelect2Refresh(countrySelect);
      })
      .catch((error) => console.error("Unable to load countries", error));
  }

  function loadStates(stateSelect) {
    const config = getConfig();
    const country = getRelatedField(stateSelect, stateSelect.dataset.countryField);
    const city = getRelatedField(stateSelect, stateSelect.dataset.cityField);
    const countryCode = country ? country.value : "";

    clearSelect(stateSelect, "Select State");
    clearSelect(city, "Select City");
    if (!config || !countryCode) {
      triggerSelect2Refresh(stateSelect);
      if (city) triggerSelect2Refresh(city);
      return Promise.resolve();
    }

    return fetchJson(config.statesUrl + "?country_code=" + encodeURIComponent(countryCode))
      .then((data) => {
        const currentValue = stateSelect.getAttribute("data-current-value") || stateSelect.value;
        const initialStateId = stateSelect.getAttribute("data-initial-state-id") || "";
        (data.states || []).forEach((state) => {
          appendOption(stateSelect, state.name, state.name, state.id);
        });
        if (currentValue) {
          stateSelect.value = currentValue;
        } else if (initialStateId) {
          const match = Array.from(stateSelect.options).find((option) => option.getAttribute("data-location-id") === initialStateId);
          if (match) stateSelect.value = match.value;
        }
        triggerSelect2Refresh(stateSelect);
      })
      .catch((error) => console.error("Unable to load states", error));
  }

  function loadCities(citySelect) {
    const config = getConfig();
    const country = getRelatedField(citySelect, citySelect.dataset.countryField);
    const state = getRelatedField(citySelect, citySelect.dataset.stateField);
    const stateId = state ? getOptionStateId(state) : "";
    const countryCode = country ? country.value : "";

    clearSelect(citySelect, "Select City");
    if (!config || !stateId) {
      triggerSelect2Refresh(citySelect);
      return Promise.resolve();
    }

    const params = new URLSearchParams();
    if (stateId) params.set("state_id", stateId);
    if (countryCode) params.set("country_code", countryCode);

    return fetchJson(config.citiesUrl + "?" + params.toString())
      .then((data) => {
        const currentValue = citySelect.getAttribute("data-current-value") || citySelect.dataset.initialValue || citySelect.value;
        (data.cities || []).forEach((city) => {
          appendOption(citySelect, city.name, city.name, city.id);
        });
        if (currentValue) citySelect.value = currentValue;
        triggerSelect2Refresh(citySelect);
      })
      .catch((error) => console.error("Unable to load cities", error));
  }

  function rememberCurrentValues(root) {
    root.querySelectorAll(".location-state-select, .location-city-select").forEach((select) => {
      if (select.value) select.setAttribute("data-current-value", select.value);
    });
  }

  function replaceWithSelect(field, placeholder) {
    if (!field) return field;

    if (field.tagName === "SELECT") {
      if (field.value && !field.getAttribute("data-current-value")) {
        field.setAttribute("data-current-value", field.value);
      }
      if (!field.options.length) {
        appendOption(field, "", placeholder);
      }
      return field;
    }

    const select = document.createElement("select");
    select.id = field.id;
    select.name = field.name || field.id;
    select.className = field.className || "form-control";
    select.required = field.required;
    select.disabled = field.disabled;
    select.setAttribute("data-current-value", field.value || "");
    appendOption(select, "", placeholder);
    if (field.value) appendOption(select, field.value, field.value);
    field.parentNode.replaceChild(select, field);
    return select;
  }

  function initShippingAddressModal(root) {
    const modal = root.querySelector ? (root.matches && root.matches("#shippingAddressModal") ? root : root.querySelector("#shippingAddressModal")) : null;
    if (!modal) return;

    const country = replaceWithSelect(modal.querySelector("#sa_country"), "Select Country");
    const state = replaceWithSelect(modal.querySelector("#sa_state"), "Select State");
    const city = replaceWithSelect(modal.querySelector("#sa_city"), "Select City");
    if (!country || !state || !city) return;

    country.classList.add("location-country-select");
    state.classList.add("location-state-select");
    city.classList.add("location-city-select");

    enhanceSelect2(country, "Select Country");
    enhanceSelect2(state, "Select State");
    enhanceSelect2(city, "Select City");

    state.dataset.countryField = "sa_country";
    state.dataset.cityField = "sa_city";
    city.dataset.countryField = "sa_country";
    city.dataset.stateField = "sa_state";

    const hiddenCountry = document.getElementById("shipping_country");
    const hiddenState = document.getElementById("shipping_state");
    const hiddenCity = document.getElementById("shipping_city");
    if (hiddenCountry && hiddenCountry.value && !country.getAttribute("data-current-value") && !country.value) {
      country.setAttribute("data-current-value", hiddenCountry.value);
    }
    if (hiddenState && hiddenState.value && !state.getAttribute("data-current-value") && !state.value) {
      state.setAttribute("data-current-value", hiddenState.value);
    }
    if (hiddenCity && hiddenCity.value && !city.getAttribute("data-current-value") && !city.value) {
      city.setAttribute("data-current-value", hiddenCity.value);
    }

    if (country.dataset.shippingLocationBound !== "1") {
      country.dataset.shippingLocationBound = "1";
      const onCountryChange = function () {
        state.removeAttribute("data-current-value");
        city.removeAttribute("data-current-value");
        loadStates(state).then(function () {
          loadCities(city);
        });
      };
      if (window.jQuery) {
        window.jQuery(country).on("change select2:select", onCountryChange);
      } else {
        country.addEventListener("change", onCountryChange);
      }
    }

    loadCountries(country).then(function () {
      loadStates(state).then(function () {
        loadCities(city);
      });
    });
  }

  function init(root) {
    root = root || document;
    if (!root.querySelectorAll) return;
    getConfig();
    rememberCurrentValues(root);
    initShippingAddressModal(root);

    root.querySelectorAll(".location-state-select").forEach((stateSelect) => {
      if (stateSelect.dataset.locationBound === "1") return;
      stateSelect.dataset.locationBound = "1";

      const country = getRelatedField(stateSelect, stateSelect.dataset.countryField);
      const city = getRelatedField(stateSelect, stateSelect.dataset.cityField);
      const onCountryChange = function () {
        stateSelect.removeAttribute("data-current-value");
        if (city) city.removeAttribute("data-current-value");
        loadStates(stateSelect).then(() => {
          if (city) loadCities(city);
        });
      };
      const onStateChange = function () {
        if (city) {
          city.removeAttribute("data-current-value");
          loadCities(city);
        }
      };
      if (country) {
        if (window.jQuery) {
          window.jQuery(country).on("change select2:select", onCountryChange);
        } else {
          country.addEventListener("change", onCountryChange);
        }
      }
      if (window.jQuery) {
        window.jQuery(stateSelect).on("change select2:select", onStateChange);
      } else {
        stateSelect.addEventListener("change", onStateChange);
      }
      loadStates(stateSelect).then(() => {
        if (city) loadCities(city);
      });
    });
  }

  window.LyraLocationSelects = {
    init: init,
    loadStates: loadStates,
    loadCities: loadCities,
  };
  window.initLocationSelects = init;

  if (!window.LyraLocationSelectsObserver) {
    window.LyraLocationSelectsObserver = new MutationObserver(function (mutations) {
      mutations.forEach(function (mutation) {
        mutation.addedNodes.forEach(function (node) {
          if (node.nodeType !== 1) return;
          if (
            node.matches(".location-state-select") ||
            node.querySelector(".location-state-select")
          ) {
            init(node.matches(".location-state-select") ? node.parentElement || document : node);
          }
        });
      });
    });
    window.LyraLocationSelectsObserver.observe(document.documentElement, {
      childList: true,
      subtree: true,
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { init(document); });
  } else {
    init(document);
  }
})();
