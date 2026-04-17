"""Mock tests for the Flask GUI.

Scope: route smoke tests + HTML landmarks + a11y metadata. Does NOT spin up
a real pipeline run — just exercises the server-rendered responses and the
static asset paths that the frontend depends on.
"""


def test_index_renders_200(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.mimetype == "text/html"


def test_index_has_a11y_landmarks(client):
    html = client.get("/").get_data(as_text=True)
    # Skip link, main landmark, live region, banner role — required for EAA/WCAG 2.2
    assert 'class="skip-link"' in html
    assert '<main id="main"' in html
    assert 'role="banner"' in html
    assert 'aria-live="polite"' in html


def test_index_has_color_scheme_meta(client):
    """Tells browsers to render native UA controls in either mode."""
    html = client.get("/").get_data(as_text=True)
    assert 'name="color-scheme"' in html
    assert 'content="dark light"' in html


def test_index_has_theme_toggle(client):
    """Theme toggle button with 3 SVG icons (auto/light/dark) present."""
    html = client.get("/").get_data(as_text=True)
    assert 'class="theme-toggle"' in html
    for cls in ("icon-auto", "icon-light", "icon-dark"):
        assert cls in html, f"missing icon class: {cls}"
    # Toggle is wired via addEventListener in app.js — no inline handler expected.


def test_index_has_fouc_prevention_script(client):
    """Inline <head> script applies stored theme before stylesheet loads."""
    html = client.get("/").get_data(as_text=True)
    assert "aijp-theme" in html  # both the inline FOUC script AND app.js reference it
    # The inline script runs before the stylesheet link
    head_start = html.find("<head>")
    link_start = html.find('rel="stylesheet"')
    script_start = html.find("localStorage.getItem('aijp-theme')")
    assert head_start < script_start < link_start


def test_index_has_mobile_tab_bar(client):
    """Bottom tab bar for mobile nav: Results + Settings (Saved removed)."""
    html = client.get("/").get_data(as_text=True)
    assert 'class="tab-bar"' in html
    assert 'data-tab="results"' in html
    assert 'data-tab="settings"' in html
    assert 'data-tab="saved"' not in html  # placeholder removed


def test_location_is_freeform_input_with_datalist(client):
    """Location accepts any string (matches CLI --location) via <input list>."""
    html = client.get("/").get_data(as_text=True)
    assert '<input type="text" id="location" list="locations"' in html
    assert '<datalist id="locations">' in html
    assert '<option value="Bangalore">' in html  # at least one suggestion


def test_cli_preview_comes_before_advanced_toggle(client):
    """Ordering: CLI preview disclosure should render above advanced-toggle
    so both disclosures open below their triggers without crossing."""
    html = client.get("/").get_data(as_text=True)
    cli_idx = html.find('class="command-preview"')
    adv_idx = html.find('class="advanced-toggle"')
    assert cli_idx != -1 and adv_idx != -1
    assert cli_idx < adv_idx


def test_mobile_advanced_settings_visible(client):
    """Advanced settings must be visible on mobile (not hidden via display:none)."""
    css = client.get("/static/style.css").get_data(as_text=True)
    # Mobile media block must NOT list advanced-toggle among hidden selectors.
    import re
    mobile_block = re.search(r"@media \(max-width: 767px\) \{([^@]+?)\}", css, re.S)
    if mobile_block:
        block = mobile_block.group(1)
        # form-row .mobile-hidden and btn-demo are OK to hide; advanced-toggle isn't.
        assert ".advanced-toggle,\n" not in block or ".advanced-toggle { display: block" in block


def test_status_has_api_key_flag(client):
    """/status must report api_key_set so the GUI can warn about missing key."""
    r = client.get("/status")
    assert r.status_code == 200
    data = r.get_json()
    assert "running" in data
    assert "api_key_set" in data
    assert isinstance(data["api_key_set"], bool)


def test_resume_exists_endpoint(client):
    """/resume/exists returns {ok: bool, path: str} for the onboarding banner."""
    r = client.get("/resume/exists")
    assert r.status_code == 200
    data = r.get_json()
    assert "ok" in data and "path" in data
    assert isinstance(data["ok"], bool)


def test_index_has_banner_and_warning_slots(client):
    """Banner + inline warning containers are in the DOM (hidden until JS shows them)."""
    html = client.get("/").get_data(as_text=True)
    assert 'id="resume-banner"' in html
    assert 'id="inline-warning"' in html


def test_index_has_open_top_control(client):
    """Stats-bar render in app.js includes the 'Open top N in tabs' button."""
    js = client.get("/static/app.js").get_data(as_text=True)
    assert "openTopNInTabs" in js
    assert 'id="open-top-n"' in js  # inside renderStats innerHTML


def test_app_js_has_sortable_columns(client):
    """Non-sortable columns (Actions, Salary, Posted Date) shouldn't get a sort handler."""
    js = client.get("/static/app.js").get_data(as_text=True)
    assert "sortable: false" in js  # TABLE_COLS config
    assert "GHOST_ORDER" in js  # ordinal map for Ghost column
    assert "no-sort" in js  # CSS class for non-sortable th
    # Salary and Posted Date are explicitly unsortable — mixed source formats
    import re
    assert re.search(r'key:\s*"Salary"[^}]+sortable:\s*false', js), "Salary should be sortable: false"
    assert re.search(r'key:\s*"Posted Date"[^}]+sortable:\s*false', js), "Posted Date should be sortable: false"


def test_css_hidden_override_for_banner(client):
    """[hidden] must win over `display: flex` on .banner and .inline-warning
    otherwise the dismiss button does nothing."""
    css = client.get("/static/style.css").get_data(as_text=True)
    import re
    # Match a rule listing banner[hidden] and/or inline-warning[hidden] → display:none !important
    assert re.search(r'\.(banner|inline-warning)\[hidden\][^{]*\{[^}]*display:\s*none\s*!important', css), \
        "banner[hidden] or inline-warning[hidden] must set display:none !important"


def test_theme_toggle_updates_title(client):
    """The theme toggle must carry a visible tooltip describing the current state."""
    js = client.get("/static/app.js").get_data(as_text=True)
    assert "_updateThemeTitle" in js
    assert "btn.title =" in js  # title is set programmatically


def test_results_returns_json_array_when_missing(client):
    """/results must return a JSON array (empty when no results file)."""
    r = client.get("/results")
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


def test_status_returns_not_running(client):
    r = client.get("/status")
    assert r.status_code == 200
    data = r.get_json()
    assert data["running"] is False
    assert "api_key_set" in data


def test_download_excel_404_when_missing(client):
    """Returns 404 when no jobs.xlsx has been generated yet."""
    r = client.get("/download/excel")
    assert r.status_code == 404


def test_static_css_served(client):
    """style.css is reachable and contains our design tokens."""
    r = client.get("/static/style.css")
    assert r.status_code == 200
    css = r.get_data(as_text=True)
    assert "--bg:" in css
    assert "--primary:" in css
    assert "prefers-color-scheme: light" in css  # light mode block exists
    assert "[data-theme=\"light\"]" in css  # explicit toggle override exists


def test_static_js_served(client):
    """app.js is reachable and exposes the theme helpers on window."""
    r = client.get("/static/app.js")
    assert r.status_code == 200
    js = r.get_data(as_text=True)
    assert "function cycleTheme" in js
    assert "THEME_KEY" in js
    assert "function applyTheme" in js
    assert "function buildCLI" in js  # CLI preview helper
    assert "function sortJobsBy" in js  # sort helper
    assert "function esc(" in js  # XSS guard still present


def test_index_has_cli_preview(client):
    """CLI equivalent preview block is in the form section."""
    html = client.get("/").get_data(as_text=True)
    assert 'class="command-preview"' in html
    assert 'id="cli-preview"' in html
    assert 'class="btn-copy"' in html


def test_index_has_icon_sprite(client):
    """Lucide SVG icon sprite is defined once and referenced in place of emoji."""
    html = client.get("/").get_data(as_text=True)
    for icon_id in (
        'id="icon-chevron-right"',
        'id="icon-search"',
        'id="icon-settings"',
        'id="icon-spreadsheet"',
        'id="icon-package"',
        'id="icon-file-text"',
        'id="icon-play"',
        'id="icon-copy"',
        'id="icon-external-link"',
    ):
        assert icon_id in html, f"missing sprite symbol: {icon_id}"
    assert 'href="#icon-play"' in html  # Run button references sprite


def test_index_has_default_pdf_style_classic(client):
    """Classic (fpdf2) is the default PDF style — keeps Playwright optional."""
    html = client.get("/").get_data(as_text=True)
    assert 'value="classic" checked' in html
    # Modern must NOT be checked (exactly one radio per group)
    assert 'value="modern" checked' not in html


def test_requirements_includes_flask(client):
    """requirements.txt lists flask so `python app.py` works out of the box."""
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "requirements.txt"), encoding="utf-8") as f:
        deps = f.read()
    assert "flask" in deps.lower()
