"""
Help Mixin — Help dialog windows for Manage Subdomains and Repository Setup.
"""
import tkinter as tk
from tkinter import scrolledtext, messagebox


class HelpMixin:
    """Methods for displaying help / user-guide dialogs."""


    def show_help(self):
        page = self.view.current_page
        if page == "repo_setup":
            self._show_repo_setup_help()
        elif page == "manage":
            self._show_subdomain_help()
        elif page == "manage_subdomain":
            self._show_manage_subdomain_help()
        elif page == "reports":
            self._show_reports_help()
        elif page == "branch_status":
            self._show_branch_status_help()
        else:
            messagebox.showinfo(
                "Help",
                "This tool allows you to manage DNS entries on your Ubuntu server.\n\n"
                "- Add and sync DNS records.\n"
                "- Use 'Test Connection' to verify server access.",
            )


    def _show_subdomain_help(self):
        win = tk.Toplevel(self.root)
        win.title("Manage Subdomains \u2014 User Guide")
        win.geometry("680x680")
        win.resizable(True, True)
        win.configure(bg="#0d1b2a")
        win.grab_set()


        tk.Label(
            win, text="Manage Subdomains \u2014 User Guide",
            font=("Segoe UI", 13, "bold"),
            bg="#0d1b2a", fg="#ffffff",
            pady=12,
        ).pack(fill="x", padx=16)

        tk.Frame(win, bg="#1565C0", height=2).pack(fill="x", padx=16)


        body = scrolledtext.ScrolledText(
            win,
            font=("Segoe UI", 10),
            bg="#0f2235", fg="#dce9f5",
            wrap=tk.WORD,
            relief=tk.FLAT,
            padx=16, pady=12,
            spacing1=2, spacing3=4,
        )
        body.pack(fill="both", expand=True, padx=16, pady=(10, 0))


        body.tag_config("section", font=("Segoe UI", 11, "bold"), foreground="#64b5f6", spacing1=10, spacing3=4)
        body.tag_config("field",   font=("Segoe UI", 10, "bold"), foreground="#80cbc4")
        body.tag_config("btn",     font=("Segoe UI", 10, "bold"), foreground="#ffb74d")
        body.tag_config("note",    font=("Segoe UI", 9,  "italic"), foreground="#90a4ae")
        body.tag_config("body",    font=("Segoe UI", 10), foreground="#dce9f5")
        body.tag_config("sep",     font=("Segoe UI", 6),  foreground="#1e3a5c")

        def write(text, tag="body"):
            body.insert(tk.END, text, tag)

        def sep():
            write("\n" + "\u2500" * 72 + "\n", "sep")


        write("\U0001f4cb  INPUT FIELDS\n", "section")
        sep()

        write("Domain Name\n", "field")
        write(
            "  Enter the subdomain you want to add to the server.\n"
            "  Example: blog.example.com  or  shop.mysite.org\n"
            "  This will create a new DNS entry pointing to the IP address below.\n\n",
            "body",
        )

        write("IP Address\n", "field")
        write(
            "  Enter the IPv4 address that the domain name should resolve to.\n"
            "  Example: 103.195.100.12\n"
            "  This is usually the public IP of your VPS or hosting server.\n\n",
            "body",
        )

        write("Filter (domain or IP)\n", "field")
        write(
            "  Type any part of a domain name or IP address to instantly filter\n"
            "  the entries shown in the table below.\n"
            "  Leave empty to show all entries.\n\n",
            "body",
        )

        write("IP Filter Dropdown\n", "field")
        write(
            "  Select a specific IP address from the dropdown to show only the\n"
            "  subdomain entries that point to that IP.\n"
            "  Choose  All IPs  to clear the IP filter.\n\n",
            "body",
        )


        write("\U0001f518  ACTION BUTTONS\n", "section")
        sep()

        write("+ Add Entry\n", "btn")
        write(
            "  Creates a new subdomain DNS record on the server using the\n"
            "  Domain Name and IP Address you entered above.\n"
            "  Both fields must be filled in before clicking this button.\n\n",
            "body",
        )

        write("Refresh\n", "btn")
        write(
            "  Reloads the subdomain list from the server.\n"
            "  Use this to see the latest entries after adding or removing records,\n"
            "  or if you think the list may be out of date.\n\n",
            "body",
        )

        write("Clear Log\n", "btn")
        write(
            "  Clears all messages from the Activity Log panel on the right.\n"
            "  Does not delete any DNS entries or affect the server.\n\n",
            "body",
        )

        write("Git Setup\n", "btn")
        write(
            "  Navigates to the  Repository Setup & Git Sync  page.\n"
            "  Use this to initialize a Git repository, connect to GitHub,\n"
            "  and push or pull code for your subdomains.\n\n",
            "body",
        )


        write("\U0001f4ca  TABLE COLUMNS\n", "section")
        sep()

        write("Domain Name\n", "field")
        write(
            "  The subdomain recorded on the server (e.g. shop.example.com).\n\n",
            "body",
        )

        write("IP Address\n", "field")
        write(
            "  The IP address the subdomain currently points to.\n\n",
            "body",
        )

        write("PDF  (\U0001f4c4)\n", "field")
        write(
            "  Click the report icon to generate and download a PDF report\n"
            "  for that specific subdomain entry.\n\n",
            "body",
        )


        write("\u2705  RECOMMENDED WORKFLOW\n", "section")
        sep()
        write(
            "  1. Enter the  Domain Name  (e.g. shop.example.com).\n"
            "  2. Enter the  IP Address  of your server.\n"
            "  3. Click  + Add Entry  to create the DNS record.\n"
            "  4. Click  Refresh  to confirm the entry appears in the table.\n"
            "  5. Use the  Filter  or  IP Filter  to quickly find entries.\n"
            "  6. Click  Git Setup  to manage source code for any subdomain.\n\n",
            "body",
        )

        body.config(state=tk.DISABLED)


        tk.Button(
            win, text="Close",
            font=("Segoe UI", 10, "bold"),
            bg="#1565C0", fg="white",
            relief=tk.FLAT, padx=20, pady=6,
            cursor="hand2",
            command=win.destroy,
        ).pack(pady=12)


    def _show_repo_setup_help(self):
        win = tk.Toplevel(self.root)
        win.title("Repository Setup \u2014 User Guide")
        win.geometry("680x750")
        win.resizable(True, True)
        win.configure(bg="#0d1b2a")
        win.grab_set()


        tk.Label(
            win, text="Repository Setup & Git Sync \u2014 User Guide",
            font=("Segoe UI", 13, "bold"),
            bg="#0d1b2a", fg="#ffffff",
            pady=12,
        ).pack(fill="x", padx=16)

        tk.Frame(win, bg="#1565C0", height=2).pack(fill="x", padx=16)


        body = scrolledtext.ScrolledText(
            win,
            font=("Segoe UI", 10),
            bg="#0f2235", fg="#dce9f5",
            wrap=tk.WORD,
            relief=tk.FLAT,
            padx=16, pady=12,
            spacing1=2, spacing3=4,
        )
        body.pack(fill="both", expand=True, padx=16, pady=(10, 0))


        body.tag_config("section", font=("Segoe UI", 11, "bold"), foreground="#64b5f6", spacing1=10, spacing3=4)
        body.tag_config("field",   font=("Segoe UI", 10, "bold"), foreground="#80cbc4")
        body.tag_config("btn",     font=("Segoe UI", 10, "bold"), foreground="#ffb74d")
        body.tag_config("note",    font=("Segoe UI", 9,  "italic"), foreground="#90a4ae")
        body.tag_config("body",    font=("Segoe UI", 10), foreground="#dce9f5")
        body.tag_config("sep",     font=("Segoe UI", 6),  foreground="#1e3a5c")

        def write(text, tag="body"):
            body.insert(tk.END, text, tag)

        def sep():
            write("\n" + "\u2500" * 72 + "\n", "sep")


        write("\U0001f4cb  INPUT FIELDS\n", "section")
        sep()

        write("Select Subdomain\n", "field")
        write(
            "  Choose the subdomain you want to set up a Git repository for.\n"
            "  The list is populated from your DNS entries. You must select one\n"
            "  before using any of the action buttons.\n\n",
            "body",
        )

        write("Repository URL (GitHub)\n", "field")
        write(
            "  Enter the HTTPS clone URL of your GitHub repository.\n"
            "  Example: https://github.com/youruser/yourrepo.git\n"
            "  This URL is used when syncing, pushing, and pulling.\n\n",
            "body",
        )

        write("GitHub Token\n", "field")
        write(
            "  Your GitHub Personal Access Token (PAT) with 'repo' scope.\n"
            "  Required to push code over HTTPS. Click the \u2699 gear icon\n"
            "  to save, view, or delete your token.\n",
            "body",
        )
        write("  \u26a0  Stored in .env \u2014 never committed to version control.\n\n", "note")

        write("Branch\n", "field")
        write(
            "  The Git branch to use for push/pull operations.\n"
            "  Defaults to  main. Use the refresh button to load branches\n"
            "  from the server.\n\n",
            "body",
        )

        write("Install Framework\n", "field")
        write(
            "  Select a framework to install during repository setup.\n"
            "  \u2022 None          \u2014 Plain project folder, no framework.\n"
            "  \u2022 Vite          \u2014 Modern front-end scaffold (React / Vue).\n"
            "  \u2022 WordPress     \u2014 Full WordPress CMS installation.\n"
            "  Selecting a framework reveals dependency checkboxes and\n"
            "  setup tool panels (see below).\n\n",
            "body",
        )

        write("Commit Message\n", "field")
        write(
            "  A short description of the changes you are pushing.\n"
            "  Example: 'Fix homepage layout' or 'Add contact form'.\n"
            "  Defaults to  'Update from server'  if left empty.\n\n",
            "body",
        )


        write("\U0001f518  ACTION BUTTONS\n", "section")
        sep()

        write("Pull & Sync\n", "btn")
        write(
            "  Connects the remote (if not already set) and pulls the latest\n"
            "  code from the selected branch to the server.\n"
            "  If the repository is not initialized, it will run git init first.\n"
            "  Use this to set up or update the server in one click.\n\n",
            "body",
        )

        write("Commit & Push\n", "btn")
        write(
            "  Stages all changed files, commits with your Commit Message,\n"
            "  and pushes to the selected branch on GitHub.\n"
            "  Requires: Git initialized, remote connected, and a GitHub Token.\n\n",
            "body",
        )

        write("File Editor\n", "btn")
        write(
            "  Opens the SFTP File Manager dialog for the selected subdomain.\n"
            "  Browse, edit, save, download, delete, and format files directly\n"
            "  on the server. Supports Prettier code formatting.\n\n",
            "body",
        )


        write("\U0001f4ca  STATUS PANEL\n", "section")
        sep()

        write("Check Status\n", "btn")
        write(
            "  Inspects the server repository and updates the status indicators:\n"
            "  \u2022 Git Repository  \u2014 whether git init has been run.\n"
            "  \u2022 Remote Connected \u2014 whether a GitHub remote URL is set.\n"
            "  \u2022 Sync Status     \u2014 whether the server is ahead, behind, or in sync.\n"
            "  \u2022 Local Changes   \u2014 how many uncommitted files exist on the server.\n\n",
            "body",
        )

        write("Clear Log\n", "btn")
        write(
            "  Clears all messages from the Git Activity Log panel.\n"
            "  Does not affect the repository or any files.\n\n",
            "body",
        )


        write("\U0001f527  WORDPRESS SETUP TOOLS\n", "section")
        sep()
        write(
            "  These tools appear when you select  WordPress (CMS)  as the\n"
            "  framework. Click the toggle to expand the setup panel.\n\n",
            "note",
        )

        write("Generate wp-config\n", "btn")
        write(
            "  Creates wp-config.php with your DB credentials and fresh\n"
            "  WordPress salt keys on the server.\n\n",
            "body",
        )

        write("Check / Create DB\n", "btn")
        write(
            "  Connects to MySQL and verifies the database exists.\n"
            "  If it does not exist, it will be created automatically.\n\n",
            "body",
        )

        write("Upload & Import SQL\n", "btn")
        write(
            "  Upload a local .sql file to the server and import it into\n"
            "  the configured MySQL database. The remote temp file is\n"
            "  cleaned up automatically after import.\n\n",
            "body",
        )

        write("Fix Permissions\n", "btn")
        write(
            "  Sets proper file/directory ownership and permissions\n"
            "  (www-data) for the WordPress installation.\n\n",
            "body",
        )

        write("Fix Apache Vhost\n", "btn")
        write(
            "  Enables AllowOverride All in the Apache virtual host config\n"
            "  so WordPress permalinks and .htaccess rules work correctly.\n\n",
            "body",
        )


        write("\u26a1  VITE DATABASE SETUP\n", "section")
        sep()
        write(
            "  These tools appear when you select  Vite (Modern Frontend)\n"
            "  as the framework. Useful if your Vite app needs a MySQL database.\n\n",
            "note",
        )

        write("Create Database\n", "btn")
        write(
            "  Connects to MySQL and creates the database if it does not exist.\n\n",
            "body",
        )

        write("Upload & Import SQL\n", "btn")
        write(
            "  Upload and import a .sql file into the configured database.\n\n",
            "body",
        )

        write("Save .env to Server\n", "btn")
        write(
            "  Writes a .env file with your DB credentials to the project\n"
            "  folder on the server. Automatically adds .env to .gitignore.\n\n",
            "body",
        )


        write("\u2705  RECOMMENDED WORKFLOW\n", "section")
        sep()
        write(
            "  1. Select a subdomain from the dropdown.\n"
            "  2. Enter the Repository URL (GitHub HTTPS clone URL).\n"
            "  3. Save your GitHub Token via the \u2699 gear icon.\n"
            "  4. Click  Pull & Sync  to initialize and pull code.\n"
            "  5. (Optional) Select a framework and configure dependencies.\n"
            "  6. Use the setup tools to configure database, permissions, etc.\n"
            "  7. Make changes and click  Commit & Push  to deploy.\n"
            "  8. Use  Check Status  at any time to verify sync state.\n\n",
            "body",
        )

        body.config(state=tk.DISABLED)


        tk.Button(
            win, text="Close",
            font=("Segoe UI", 10, "bold"),
            bg="#1565C0", fg="white",
            relief=tk.FLAT, padx=20, pady=6,
            cursor="hand2",
            command=win.destroy,
        ).pack(pady=12)


    def _show_manage_subdomain_help(self):
        win = tk.Toplevel(self.root)
        win.title("Manage Subdomain \u2014 User Guide")
        win.geometry("680x720")
        win.resizable(True, True)
        win.configure(bg="#0d1b2a")
        win.grab_set()

        tk.Label(
            win, text="Manage Subdomain \u2014 User Guide",
            font=("Segoe UI", 13, "bold"),
            bg="#0d1b2a", fg="#ffffff", pady=12,
        ).pack(fill="x", padx=16)

        tk.Frame(win, bg="#1565C0", height=2).pack(fill="x", padx=16)

        body = scrolledtext.ScrolledText(
            win, font=("Segoe UI", 10),
            bg="#0f2235", fg="#dce9f5",
            wrap=tk.WORD, relief=tk.FLAT,
            padx=16, pady=12, spacing1=2, spacing3=4,
        )
        body.pack(fill="both", expand=True, padx=16, pady=(10, 0))

        body.tag_config("section", font=("Segoe UI", 11, "bold"), foreground="#64b5f6", spacing1=10, spacing3=4)
        body.tag_config("field",   font=("Segoe UI", 10, "bold"), foreground="#80cbc4")
        body.tag_config("btn",     font=("Segoe UI", 10, "bold"), foreground="#ffb74d")
        body.tag_config("note",    font=("Segoe UI", 9,  "italic"), foreground="#90a4ae")
        body.tag_config("body",    font=("Segoe UI", 10), foreground="#dce9f5")
        body.tag_config("sep",     font=("Segoe UI", 6),  foreground="#1e3a5c")

        def write(text, tag="body"):
            body.insert(tk.END, text, tag)

        def sep():
            write("\n" + "\u2500" * 72 + "\n", "sep")


        write("\U0001f4cb  PAGE OVERVIEW\n", "section")
        sep()
        write(
            "  This page shows all subdomains on your server in a table view.\n"
            "  Each row displays the domain, IP, Git status, remote status,\n"
            "  and quick-action buttons for managing that subdomain.\n\n",
            "body",
        )


        write("\U0001f4ca  LIVE METRIC CARDS\n", "section")
        sep()

        write("SSL Expiring\n", "field")
        write(
            "  Number of subdomains whose SSL/TLS certificate will expire\n"
            "  within the next 30 days. Renew them promptly to avoid downtime.\n\n",
            "body",
        )

        write("Down\n", "field")
        write(
            "  Subdomains that returned a 5xx error or timed out when probed\n"
            "  via HTTP. These sites may be down or misconfigured.\n\n",
            "body",
        )

        write("Connections\n", "field")
        write(
            "  Current number of established TCP connections on the server\n"
            "  (sourced from socket statistics).\n\n",
            "body",
        )

        write("Load Avg\n", "field")
        write(
            "  1-minute load average. Values above your CPU core count may\n"
            "  indicate high server load.\n\n",
            "body",
        )

        write("Processes\n", "field")
        write(
            "  Total number of running processes on the server.\n"
            "  A sudden spike may indicate runaway processes.\n\n",
            "body",
        )


        write("\U0001f5c2  TABLE COLUMNS\n", "section")
        sep()

        write("Domain Name\n", "field")
        write("  The subdomain hostname (e.g. shop.example.com).\n\n", "body")

        write("IP Address\n", "field")
        write("  The IPv4 address the subdomain currently resolves to.\n\n", "body")

        write("Git\n", "field")
        write(
            "  Shows whether a Git repository has been initialized in the\n"
            "  subdomain's web root folder on the server.\n"
            "  \u2022 \u2714  = Git repo exists     \u2022 \u2718  = No repo found\n\n",
            "body",
        )

        write("Remote\n", "field")
        write(
            "  Shows whether a GitHub remote URL has been configured.\n"
            "  \u2022 \u2714  = Remote connected    \u2022 \u2718  = No remote\n\n",
            "body",
        )

        write("PDF\n", "field")
        write(
            "  Click the PDF icon to generate a subdomain health report.\n"
            "  The report is saved as a PDF in the reports/ folder.\n\n",
            "body",
        )

        write("Action\n", "field")
        write(
            "  Click to open a context menu with available actions\n"
            "  for that subdomain (see Action Menu below).\n\n",
            "body",
        )


        write("\U0001f518  ACTION MENU (Right-click or Action column)\n", "section")
        sep()

        write("Upload Project\n", "btn")
        write(
            "  Opens a dialog to upload a local project folder to the server.\n"
            "  Supports framework selection (WordPress / Vite) with optional\n"
            "  dependency installation, database setup, and SQL import.\n\n",
            "body",
        )

        write("Connect Git\n", "btn")
        write(
            "  Opens a dialog to connect an existing GitHub repository to the\n"
            "  subdomain on the server. If the repo already has a remote, it\n"
            "  will be pre-filled automatically.\n\n",
            "body",
        )

        write("File Manager\n", "btn")
        write(
            "  Opens the SFTP File Manager dialog. Browse, edit, download,\n"
            "  delete, and format files directly on the server. Supports\n"
            "  Prettier code formatting and Apache restart.\n\n",
            "body",
        )

        write("Repo Setup\n", "btn")
        write(
            "  Navigates to the Repository Setup page with the subdomain\n"
            "  pre-selected, for Git sync, commit/push, and branch management.\n\n",
            "body",
        )

        write("Delete\n", "btn")
        write(
            "  Deletes the subdomain DNS entry from the server.\n"
            "  This removes the DNS record but does not delete files.\n\n",
            "body",
        )


        write("\u2699  CONTROLS\n", "section")
        sep()

        write("Filter\n", "field")
        write(
            "  Type any domain or IP to instantly filter the table rows.\n\n",
            "body",
        )

        write("IP Filter Dropdown\n", "field")
        write(
            "  Select a specific IP to show only subdomains pointing to it.\n\n",
            "body",
        )

        write("Refresh\n", "btn")
        write(
            "  Reloads the subdomain list and re-checks Git/remote status.\n\n",
            "body",
        )

        write("Branch\n", "field")
        write(
            "  Set the default Git branch name used for repository operations.\n"
            "  Defaults to  main.\n\n",
            "body",
        )

        body.config(state=tk.DISABLED)

        tk.Button(
            win, text="Close",
            font=("Segoe UI", 10, "bold"),
            bg="#1565C0", fg="white",
            relief=tk.FLAT, padx=20, pady=6,
            cursor="hand2", command=win.destroy,
        ).pack(pady=12)


    def _show_reports_help(self):
        win = tk.Toplevel(self.root)
        win.title("Reports \u2014 User Guide")
        win.geometry("680x650")
        win.resizable(True, True)
        win.configure(bg="#0d1b2a")
        win.grab_set()

        tk.Label(
            win, text="Reports \u2014 User Guide",
            font=("Segoe UI", 13, "bold"),
            bg="#0d1b2a", fg="#ffffff", pady=12,
        ).pack(fill="x", padx=16)

        tk.Frame(win, bg="#1565C0", height=2).pack(fill="x", padx=16)

        body = scrolledtext.ScrolledText(
            win, font=("Segoe UI", 10),
            bg="#0f2235", fg="#dce9f5",
            wrap=tk.WORD, relief=tk.FLAT,
            padx=16, pady=12, spacing1=2, spacing3=4,
        )
        body.pack(fill="both", expand=True, padx=16, pady=(10, 0))

        body.tag_config("section", font=("Segoe UI", 11, "bold"), foreground="#64b5f6", spacing1=10, spacing3=4)
        body.tag_config("field",   font=("Segoe UI", 10, "bold"), foreground="#80cbc4")
        body.tag_config("btn",     font=("Segoe UI", 10, "bold"), foreground="#ffb74d")
        body.tag_config("note",    font=("Segoe UI", 9,  "italic"), foreground="#90a4ae")
        body.tag_config("body",    font=("Segoe UI", 10), foreground="#dce9f5")
        body.tag_config("sep",     font=("Segoe UI", 6),  foreground="#1e3a5c")

        def write(text, tag="body"):
            body.insert(tk.END, text, tag)

        def sep():
            write("\n" + "\u2500" * 72 + "\n", "sep")


        write("\U0001f4cb  PAGE OVERVIEW\n", "section")
        sep()
        write(
            "  This page lists all generated PDF reports for your subdomains.\n"
            "  Reports are created from the Manage Subdomain page (PDF column)\n"
            "  and are stored in the  reports/  folder.\n\n",
            "body",
        )


        write("\U0001f5c2  REPORT TABLE\n", "section")
        sep()

        write("Subdomain\n", "field")
        write("  The subdomain the report was generated for.\n\n", "body")

        write("Date\n", "field")
        write("  When the report was generated (extracted from the filename).\n\n", "body")

        write("Size\n", "field")
        write("  File size of the PDF report.\n\n", "body")

        write("Status\n", "field")
        write("  Whether the report file exists and is readable.\n\n", "body")


        write("\U0001f518  ACTION BUTTONS\n", "section")
        sep()

        write("Export DNS CSV\n", "btn")
        write(
            "  Exports all current DNS subdomain entries to a CSV file.\n"
            "  Opens a Save dialog to choose the output location.\n\n",
            "body",
        )

        write("Export Activity CSV\n", "btn")
        write(
            "  Exports the application activity log (all recorded actions)\n"
            "  to a CSV file. Useful for audit trails and record-keeping.\n\n",
            "body",
        )

        write("Refresh\n", "btn")
        write(
            "  Rescans the  reports/  folder and reloads the table with\n"
            "  any new or deleted reports.\n\n",
            "body",
        )


        write("\U0001f4c4  PDF PREVIEW\n", "section")
        sep()
        write(
            "  Double-click a report in the table to open a preview.\n"
            "  If PyMuPDF is installed, a rendered preview is shown in the\n"
            "  right panel with page navigation.\n\n",
            "body",
        )

        write("Page Navigation\n", "field")
        write(
            "  Use the \u25c0 and \u25b6 arrows to move between pages of the PDF.\n"
            "  The current page number is displayed between the arrows.\n\n",
            "body",
        )

        write("Open\n", "btn")
        write(
            "  Opens the PDF in your system's default PDF viewer.\n\n",
            "body",
        )


        write("\u2699  CONTEXT MENU (Right-click)\n", "section")
        sep()
        write(
            "  Right-click on a report row to see additional options:\n"
            "  \u2022 Open Report    \u2014 Opens the PDF in the default viewer.\n"
            "  \u2022 Show in Folder \u2014 Opens the folder containing the PDF.\n"
            "  \u2022 Delete Report  \u2014 Permanently deletes the report file.\n\n",
            "body",
        )


        write("\U0001f50d  FILTER\n", "section")
        sep()
        write(
            "  Type in the filter field to search reports by subdomain name.\n"
            "  The table updates instantly as you type.\n\n",
            "body",
        )

        body.config(state=tk.DISABLED)

        tk.Button(
            win, text="Close",
            font=("Segoe UI", 10, "bold"),
            bg="#1565C0", fg="white",
            relief=tk.FLAT, padx=20, pady=6,
            cursor="hand2", command=win.destroy,
        ).pack(pady=12)


    def _show_branch_status_help(self):
        win = tk.Toplevel(self.root)
        win.title("Branch Deployment Status \u2014 User Guide")
        win.geometry("680x580")
        win.resizable(True, True)
        win.configure(bg="#0d1b2a")
        win.grab_set()

        tk.Label(
            win, text="Branch Deployment Status \u2014 User Guide",
            font=("Segoe UI", 13, "bold"),
            bg="#0d1b2a", fg="#ffffff", pady=12,
        ).pack(fill="x", padx=16)

        tk.Frame(win, bg="#1565C0", height=2).pack(fill="x", padx=16)

        body = scrolledtext.ScrolledText(
            win, font=("Segoe UI", 10),
            bg="#0f2235", fg="#dce9f5",
            wrap=tk.WORD, relief=tk.FLAT,
            padx=16, pady=12, spacing1=2, spacing3=4,
        )
        body.pack(fill="both", expand=True, padx=16, pady=(10, 0))

        body.tag_config("section", font=("Segoe UI", 11, "bold"), foreground="#64b5f6", spacing1=10, spacing3=4)
        body.tag_config("field",   font=("Segoe UI", 10, "bold"), foreground="#80cbc4")
        body.tag_config("btn",     font=("Segoe UI", 10, "bold"), foreground="#ffb74d")
        body.tag_config("note",    font=("Segoe UI", 9,  "italic"), foreground="#90a4ae")
        body.tag_config("body",    font=("Segoe UI", 10), foreground="#dce9f5")
        body.tag_config("sep",     font=("Segoe UI", 6),  foreground="#1e3a5c")

        def write(text, tag="body"):
            body.insert(tk.END, text, tag)

        def sep():
            write("\n" + "\u2500" * 72 + "\n", "sep")


        write("\U0001f4cb  PAGE OVERVIEW\n", "section")
        sep()
        write(
            "  This page shows the Git branch currently checked out (deployed)\n"
            "  on the server for each subdomain that has a Git repository.\n"
            "  Use it to quickly verify which branch is live on each site.\n\n",
            "body",
        )


        write("\U0001f5c2  TABLE COLUMNS\n", "section")
        sep()

        write("Subdomain\n", "field")
        write("  The subdomain hostname on the server.\n\n", "body")

        write("Branch\n", "field")
        write(
            "  The Git branch currently checked out in the subdomain's\n"
            "  web root folder (e.g. main, develop, feature/xyz).\n"
            "  If no branch is detected, it may show  (unknown).\n\n",
            "body",
        )

        write("Status\n", "field")
        write(
            "  Whether the Git repo is clean or has uncommitted changes.\n"
            "  \u2022 Clean    \u2014 No uncommitted changes on the server.\n"
            "  \u2022 Modified \u2014 There are uncommitted changes in the working tree.\n\n",
            "body",
        )

        write("Last Commit\n", "field")
        write(
            "  The most recent commit message and date on the deployed branch.\n"
            "  Helps identify what version of the code is currently live.\n\n",
            "body",
        )


        write("\U0001f518  CONTROLS\n", "section")
        sep()

        write("Refresh\n", "btn")
        write(
            "  Re-scans all subdomains on the server and updates the branch\n"
            "  information for each one. This connects via SSH and runs\n"
            "  git status on each subdomain folder.\n\n",
            "body",
        )

        write("Filter\n", "field")
        write(
            "  Type any part of a subdomain name or branch name to instantly\n"
            "  filter the table. Leave empty to show all entries.\n\n",
            "body",
        )


        write("\u2705  TIPS\n", "section")
        sep()
        write(
            "  \u2022 Use this page to verify that the correct branch is deployed\n"
            "    before going live or after a push.\n"
            "  \u2022 If a subdomain shows  (unknown), it may not have a Git repo.\n"
            "    Use  Repository Setup  to initialize one.\n"
            "  \u2022 If  Status  shows  Modified, go to  Repository Setup  and use\n"
            "    Commit & Push  to commit the changes or  Pull & Sync  to\n"
            "    reset to the remote branch.\n\n",
            "body",
        )

        body.config(state=tk.DISABLED)

        tk.Button(
            win, text="Close",
            font=("Segoe UI", 10, "bold"),
            bg="#1565C0", fg="white",
            relief=tk.FLAT, padx=20, pady=6,
            cursor="hand2", command=win.destroy,
        ).pack(pady=12)
