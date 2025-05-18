# CSV Filtering App

![win11dash](https://github.com/user-attachments/assets/f1b1e246-8240-4023-9129-1e54b8422929)

A simple, open-source dashboard for managing, filtering, and tracking bulk assets or projects based on CSV data. Originally built for planning and scheduling Windows 11 workstation upgrades at Computer Networking Solutions, Inc. (CNS), this app can be repurposed for any scenario where you need to view, search, filter, update, and export CSV-based lists.

## Features

- CSV import: Upload a CSV to initialize or replace the database.
- Instant search and filter by any field.
- Grouping by a key column (e.g., "Client Name") with collapsible/expandable groups.
- In-place editing for select fields (e.g., status, technician, notes).
- Export filtered view to CSV.
- Responsive, modern interface.

## Getting Started

1. Install requirements:
   `pip install -r requirements.txt`

2. Run the app:
   `uvicorn main:app --reload`

   Or specify port/host (for example, to use port 1337):
   `uvicorn main:app --reload --port 1337 --host 0.0.0.0`

3. Open your browser to:
   `http://localhost:8000  (or your chosen port/host)`

## Usage

- Import a CSV via the form at the bottom of the dashboard (this wipes and replaces all data).
- Use filter boxes at the top to instantly filter/search. Use the "×" to clear individual filters or "Clear" to reset all.
- Update statuses, technicians, or notes directly in the table; changes are saved instantly.
- Click "Export CSV" to download the currently filtered dataset.

## CSV Format

Your CSV should contain headers in the first row.
For the default Windows 11 upgrade case, the columns expected are:

  `Client Name, Computer Name, RAM_GB, Processor Name, DiskSpaceRemaining_GB`

You can adapt the column names/logic for your own scenario.

Example:
`Client Name,Computer Name,RAM_GB,Processor Name,DiskSpaceRemaining_GB
Acme,PC-001,16,Intel i7-8700,512
Fabrikam,PC-002,8,Intel i5-8500,128`

## Customization

- To adjust grouping or fields, edit `models.py`, `utils.py`, and the dashboard Jinja2 template.
- The default technician and status lists are in `main.py`.

## License

Open-source. Free for personal or commercial use. No warranty is provided.

## Acknowledgments

Originally developed by Steven for Computer Networking Solutions, Inc. (CNS) for internal Windows 11 upgrade project management.

## Support

Community support only. Please open an issue or submit a pull request for improvements.
