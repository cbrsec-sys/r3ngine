# Custom Parameter Discovery Engine (CPDE)

The Custom Parameter Discovery Engine (CPDE) allows users to define custom regular expressions and keyword matchers to extract sensitive or high-value parameters across scan results. By configuring these parameters in the r3ngine settings, the system will automatically scan and flag matching parameters during the web enumeration and crawling phases.

## Overview

Modern web applications often embed custom, non-standard parameters in URLs and POST bodies that indicate administrative access, feature flags, or potential injection vectors. CPDE enables you to track these specific parameters globally.

### Key Features
- **Regex & String Matching:** Match parameters by exact names or regular expressions.
- **Severity Levels:** Assign severity to parameters (e.g., `Critical` for `admin_token`, `Info` for `lang_id`).
- **Description & Context:** Provide descriptions so team members understand the context of the custom parameter.
- **Scan Integration:** When a scan discovers a URL containing the defined parameters, it is automatically flagged and highlighted in the scan results.

## Configuration

To configure custom parameters:

1. Navigate to **Settings** -> **Custom Parameters** in the left sidebar.
2. Click **ADD CUSTOM PARAMETER**.
3. Fill out the form:
   - **Parameter Name:** The name or regex pattern to search for.
   - **Type:** Choose either `regex` or `string`.
   - **Severity:** Select the severity level (`Critical`, `High`, `Medium`, `Low`, `Info`, `Unknown`).
   - **Description:** An optional description of why this parameter is important.
4. Click **SAVE** to add the parameter to the engine.

## Viewing Results

When a scan discovers URLs with matching parameters, they are aggregated and displayed in the scan results.

1. Open a **Scan Detail** page.
2. Navigate to the **Parameters** tab.
3. The table will display all discovered custom parameters, the number of occurrences, the URLs where they were found, and their severity.
4. Clicking on the URL count will expand a sub-table containing the exact endpoint URLs.

## Implementation Details

CPDE integrates natively into the r3ngine database and scanning pipeline:
- **Database Model:** The `Parameter` model stores the custom parameter definitions, including `name`, `type`, `severity`, and `description`.
- **API Endpoints:** Managed via the `/api/settings/parameters/` REST API.
- **Frontend UI:** Integrated into the Settings panel and Scan Detail tabs using React and Material-UI.

By defining a comprehensive list of custom parameters, security teams can automate the discovery of hidden attack surfaces and undocumented application features across large scopes.
