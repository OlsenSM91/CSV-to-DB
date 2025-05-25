Certainly! Here’s an **overhauled, modernized README** for your app, reflecting the new features and ConnectWise ticket integration. This version is cleaner, less repetitive, and focuses on your actual value.

---

# CNS Asset Dashboard

![stats\_added](https://github.com/user-attachments/assets/bc338ec2-ac43-45ca-b1bf-569242295ff5)
![projectTicket](https://github.com/user-attachments/assets/069dc1cb-b7db-4c81-a6cf-d8c94dd31766)

A modern, open-source web dashboard for managing and scheduling workstation or asset upgrades in bulk. Originally built for Windows 11 upgrade planning at Computer Networking Solutions, Inc. (CNS), this tool now supports advanced tracking, CSV import/export, real-time status editing, and direct integration with ConnectWise for ticket automation.

---

## Key Features

* **CSV Import/Replace:** Upload a CSV file to initialize or reset all data.
* **Instant, Multi-Field Filtering:** Instantly search and filter workstations by client, RAM, technician, status, or any other field. Filtered results are always live and exportable.
* **Group & Collapse by Client:** Workstations are grouped by client/company with collapsible sections for easier navigation.
* **In-Place, Live Editing:** Change statuses, technician assignments, or notes inline—changes are instantly saved.
* **Workstation CRUD:** Add, edit, or remove workstations directly from the dashboard.
* **Export Filtered Results:** Download your currently filtered view as a CSV for reporting or further processing.
* **Upgrade Status Overview:** See real-time statistics for all workstations (including “Ready to Upgrade,” “Completed,” “Not Started,” and more).
* **ConnectWise Ticketing Integration:**

  * Automatically enable the “Create Ticket” button only when all company workstations are properly assigned and updated.
  * Seamlessly create a grouped ConnectWise service ticket for eligible companies—pre-filled with upgrade details and technician assignments.

---

## Quick Start

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure ConnectWise Integration:**
   Create a `.env` file in your project directory:

   ```
   CW_BASE_URL=https://yourinstance.connectwise.com/v4_6_release/apis/3.0
   CW_COMPANY_ID=YOURCOMPANYID
   CW_CLIENT_ID=YOUR_CLIENT_ID
   CW_PUBLIC_API_KEY=YOUR_PUBLIC_KEY
   CW_PRIVATE_API_KEY=YOUR_PRIVATE_KEY
   ```

   *(Contact your ConnectWise admin for API credentials if needed.)*

3. **Run the app:**

   ```bash
   uvicorn main:app --reload
   ```

   Or specify a custom port/host if needed.

4. **Open in your browser:**

   ```
   http://localhost:8000
   ```

   (or your chosen host/port)

---

## Usage Overview

* **Import Data:** Upload your CSV at the bottom of the dashboard to (re)populate the app.
* **Filter/Search:** Use the multi-field filters at the top for instant narrowing by client, RAM, technician, status, and more. Filters are stackable.
* **Edit Inline:** Click directly on fields like status or technician to change them—no extra forms needed.
* **Add/Remove Workstations:** Use the buttons in each group to quickly edit or add new systems.
* **Export Data:** Download your current filtered view with one click—great for reporting or off-line work.
* **Create Project Ticket (ConnectWise):**

  * When all workstations for a company are ready (i.e., each has a technician and status), a “Create Project Ticket” button appears for that group.
  * Clicking this button sends a grouped, detailed ticket to ConnectWise under the appropriate service board, with summary, description, assigned technicians, and more.

---

## CSV Format

Your input CSV should have headers as the first row, such as:

```
Client Name,Computer Name,RAM_GB,Processor Name,DiskSpaceRemaining_GB,Status,Technician,Notes
Acme,PC-001,16,Intel i7-8700,512,Ready to Upgrade,Steven,Customer approved
```

Additional columns can be added; required columns may depend on your deployment.

---

## Customization & Extensibility

* **Field Logic:** Adjust grouping or field logic in `models.py`, `utils.py`, and `dashboard.html` (Jinja2).
* **Technician/Status Lists:** Update valid lists in `main.py`.
* **ConnectWise Integration:** Edit board/type/team defaults in `connectwise_api.py` if you have multiple boards or types.
* **Permissions:** For ConnectWise features, API credentials must have sufficient permissions for ticket creation and member/team lookups.

---

## License

Open-source. Free for business or personal use. No warranty provided.

---

## Credits

Developed by Steven Olsen for Computer Networking Solutions, Inc. (CNS). Released for public use and IT community benefit.

---

**Contributions welcome!** Open an issue or submit a PR with improvements or fixes.
