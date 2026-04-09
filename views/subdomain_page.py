"""
Subdomain Page View — the form and activity log for managing subdomain entries.
Lives on its own page (frame) that the controller can show / hide.
"""
import tkinter as tk
from tkinter import scrolledtext

from models.config import COLORS, DEFAULT_IP_ADDRESS, save_default_ip_address, clear_default_ip_address
from views.widgets import ModernEntry, ModernButton, RoundedFrame


DNS_SUFFIX = ".veryapp.info"


def _create_label(parent, text, font_size=10, bold=False, color="text_secondary"):
    weight = "bold" if bold else "normal"
    return tk.Label(
        parent, text=text,
        font=("Segoe UI", font_size, weight),
        bg=parent.cget("bg"), fg=COLORS[color],
    )


class SubdomainPageView:
    """Self-contained page frame for subdomain CRUD.
    The controller binds button callbacks after construction."""

    def __init__(self, parent):

        self.frame = tk.Frame(parent, bg=COLORS["bg_primary"])
        self.dns_suffix = DNS_SUFFIX
        self._ip_address = DEFAULT_IP_ADDRESS
        self._wizard_step = 1
        self._known_domains = set()
        self._build()


    def _build(self):
        container = tk.Frame(self.frame, bg=COLORS["bg_primary"], padx=24, pady=16)
        container.pack(fill="both", expand=True)


        title_bar = tk.Frame(container, bg=COLORS["bg_primary"])
        title_bar.pack(fill="x", pady=(0, 12))

        tk.Label(
            title_bar, text="Add Subdomain Entry",
            font=("Segoe UI", 16, "bold"),
            bg=COLORS["bg_primary"], fg=COLORS["text_primary"],
        ).pack(side="left")


        content_frame = tk.Frame(container, bg=COLORS["bg_primary"])
        content_frame.pack(fill="both", expand=True)
        content_frame.columnconfigure(0, weight=1, minsize=420)
        content_frame.columnconfigure(1, weight=1, minsize=280)
        content_frame.rowconfigure(0, weight=1)


        form_card = RoundedFrame(
            content_frame, bg_color=COLORS["bg_secondary"],
            radius=14, padding=(12, 12),
        )
        form_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        form_section = form_card.inner


        header_row = tk.Frame(form_section, bg=COLORS["bg_secondary"])
        header_row.pack(fill="x", pady=(0, 4))

        _create_label(header_row, "Add New Subdomain", 11, True).pack(side="left")

        self.settings_btn = tk.Button(
            header_row, text="\u2699",
            font=("Segoe UI", 14), relief="flat", cursor="hand2",
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
            activebackground=COLORS["bg_secondary"],
            activeforeground=COLORS["text_primary"],
            bd=0, highlightthickness=0,
            command=self._open_ip_settings,
        )
        self.settings_btn.pack(side="right")


        input_section = tk.Frame(form_section, bg=COLORS["bg_secondary"])
        input_section.pack(fill="x", pady=(6, 10))
        input_section.columnconfigure(0, weight=1)

        self._step_indicator_label = tk.Label(
            input_section,
            text="Step 1 of 3: Domain Input",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_secondary"], fg=COLORS["warning"],
            anchor="w",
        )
        self._step_indicator_label.pack(fill="x", pady=(0, 8))

        self._progress_frame = tk.Frame(input_section, bg=COLORS["bg_secondary"])
        self._progress_frame.pack(fill="x", pady=(0, 10))
        self._progress_dots = []
        for idx in range(1, 4):
            dot = tk.Label(
                self._progress_frame,
                text=str(idx),
                font=("Segoe UI", 8, "bold"),
                bg=COLORS["bg_accent"], fg=COLORS["text_secondary"],
                width=3, height=1,
            )
            dot.pack(side="left", padx=(0, 6))
            self._progress_dots.append(dot)

        self.step1_frame = tk.Frame(input_section, bg=COLORS["bg_secondary"])
        self.step2_frame = tk.Frame(input_section, bg=COLORS["bg_secondary"])
        self.step3_frame = tk.Frame(input_section, bg=COLORS["bg_secondary"])


        subdomain_frame = tk.Frame(self.step1_frame, bg=COLORS["bg_secondary"])
        subdomain_frame.pack(fill="x")

        _create_label(subdomain_frame, "Subdomain Name", 10, True).pack(anchor="w")


        entry_with_suffix = tk.Frame(subdomain_frame, bg=COLORS["bg_secondary"])
        entry_with_suffix.pack(fill="x", pady=(4, 0))
        entry_with_suffix.columnconfigure(0, weight=1)

        self.subdomain_entry = ModernEntry(
            entry_with_suffix, font=("Segoe UI", 11), width=20
        )
        self.subdomain_entry.pack(side="left", fill="x", expand=True, ipady=4)


        suffix_label = tk.Label(
            entry_with_suffix, text=self.dns_suffix,
            font=("Segoe UI", 11),
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
            padx=8, pady=4,
        )
        suffix_label.pack(side="left", fill="y")


        self.subdomain_entry.bind("<KeyRelease>", self._update_domain_preview)


        self.domain_preview_label = tk.Label(
            subdomain_frame, text="Full domain: (enter subdomain above)",
            font=("Segoe UI", 9),
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
        )
        self.domain_preview_label.pack(anchor="w", pady=(4, 0))

        self.domain_availability_label = tk.Label(
            subdomain_frame,
            text="Availability: Enter a subdomain to check",
            font=("Segoe UI", 9),
            bg=COLORS["bg_secondary"],
            fg=COLORS["text_secondary"],
            anchor="w",
        )
        self.domain_availability_label.pack(anchor="w", pady=(3, 0))


        ip_status_frame = tk.Frame(self.step2_frame, bg=COLORS["bg_secondary"])
        ip_status_frame.pack(fill="x", pady=(6, 0))

        _create_label(ip_status_frame, "IP Address", 10, True).pack(anchor="w")

        self._ip_status_label = tk.Label(
            ip_status_frame,
            text="",
            font=("Segoe UI", 9),
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
            anchor="w",
        )
        self._ip_status_label.pack(anchor="w", pady=(2, 0))
        self._refresh_ip_status()

        self.ip_var = tk.StringVar(value=self._ip_address)
        self.ip_var.trace_add("write", lambda *_: self._update_next_button_state())

        ip_entry_frame = tk.Frame(self.step2_frame, bg=COLORS["bg_secondary"])
        ip_entry_frame.pack(fill="x", pady=(8, 0))
        _create_label(ip_entry_frame, "Target Server IP", 10, True).pack(anchor="w")

        self._ip_entry_widget = tk.Entry(
            ip_entry_frame,
            textvariable=self.ip_var,
            font=("Segoe UI", 11), relief="flat",
            bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"],
        )
        self._ip_entry_widget.pack(fill="x", ipady=6, pady=(4, 0))
        self._ip_entry_widget.bind("<KeyRelease>", lambda e: self._update_next_button_state())

        self._use_default_var = tk.BooleanVar(value=bool(self._ip_address))
        use_default_row = tk.Frame(self.step2_frame, bg=COLORS["bg_secondary"])
        use_default_row.pack(fill="x", pady=(6, 0))
        self._use_default_chk = tk.Checkbutton(
            use_default_row,
            text="Use saved default IP",
            variable=self._use_default_var,
            font=("Segoe UI", 9),
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
            selectcolor=COLORS["bg_primary"],
            activebackground=COLORS["bg_secondary"],
            activeforeground=COLORS["text_primary"],
            anchor="w",
            command=self._toggle_use_default_ip,
        )
        self._use_default_chk.pack(anchor="w")

        self._ip_help_label = tk.Label(
            ip_entry_frame,
            text="Confirm where the subdomain A record will point.",
            font=("Segoe UI", 8),
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
            anchor="w",
        )
        self._ip_help_label.pack(fill="x", pady=(4, 0))

        preview_card = tk.Frame(self.step3_frame, bg=COLORS["bg_accent"], padx=10, pady=10)
        preview_card.pack(fill="x")
        _create_label(preview_card, "Preview & Confirm", 10, True, color="text_primary").pack(anchor="w")

        self._preview_domain_label = tk.Label(
            preview_card,
            text="Domain: —",
            font=("Segoe UI", 9),
            bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
            anchor="w",
        )
        self._preview_domain_label.pack(fill="x", pady=(6, 0))

        self._preview_ip_label = tk.Label(
            preview_card,
            text="Target IP: —",
            font=("Segoe UI", 9),
            bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
            anchor="w",
        )
        self._preview_ip_label.pack(fill="x", pady=(2, 0))

        self._preview_action_label = tk.Label(
            preview_card,
            text="Actions: Create server entry and register Vultr DNS A record.",
            font=("Segoe UI", 9),
            bg=COLORS["bg_accent"], fg=COLORS["text_secondary"],
            anchor="w", justify="left",
        )
        self._preview_action_label.pack(fill="x", pady=(6, 0))

        self._confirm_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            self.step3_frame,
            text="I confirm the domain and target IP are correct.",
            variable=self._confirm_var,
            font=("Segoe UI", 9),
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
            selectcolor=COLORS["bg_primary"],
            activebackground=COLORS["bg_secondary"],
            activeforeground=COLORS["text_primary"],
            anchor="w",
            command=self._update_add_button_state,
        ).pack(fill="x", pady=(8, 0))


        self.domain_entry = tk.Entry(subdomain_frame, font=("Segoe UI", 11), width=30)


        button_frame = tk.Frame(form_section, bg=COLORS["bg_secondary"])
        button_frame.pack(fill="x", pady=(12, 0))

        self.prev_step_btn = tk.Button(
            button_frame, text="← Back",
            font=("Segoe UI", 9), relief="flat", cursor="hand2",
            bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
            activebackground="#0a2a4a", activeforeground=COLORS["text_primary"],
            command=lambda: self._go_to_step(self._wizard_step - 1),
        )
        self.prev_step_btn.pack(side="left", ipadx=8, ipady=5)

        self.next_step_btn = tk.Button(
            button_frame, text="Next →",
            font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
            bg=COLORS["accent"], fg="white",
            activebackground=COLORS["button_hover"], activeforeground="white",
            command=self._on_next_step,
        )
        self.next_step_btn.pack(side="left", padx=(8, 8), ipadx=8, ipady=5)

        self.add_btn = ModernButton(
            button_frame, text="+ Add Entry", command=None,
            bg_color=COLORS["success"], hover_color="#3db892",
            border_color="#3da17f", width=120, height=30,
        )
        self.add_btn.pack(side="left", padx=(0, 8))

        self.refresh_btn = ModernButton(
            button_frame, text="Refresh", command=None,
            bg_color="#F57C00", hover_color="#ff8c00",
            border_color="#cc6600", width=100, height=30,
        )
        self.refresh_btn.pack(side="left", padx=8)

        self.clear_btn = ModernButton(
            button_frame, text="Clear Log", command=None,
            bg_color=COLORS["bg_accent"], hover_color="#0a2a4a",
            border_color="#0a2540", width=100, height=30,
        )
        self.clear_btn.pack(side="left", padx=8)

        self.git_setup_btn = ModernButton(
            button_frame, text="Git Setup", command=None,
            bg_color="#7B1FA2", hover_color="#6A1B9A",
            border_color="#4A148C", width=100, height=30,
        )
        self.git_setup_btn.pack(side="left", padx=8)


        log_card = RoundedFrame(
            content_frame, bg_color=COLORS["bg_secondary"],
            radius=14, padding=(12, 12),
        )
        log_card.grid(row=0, column=1, sticky="nsew")
        log_section = log_card.inner

        _create_label(log_section, "Activity Log:", 10, True).pack(anchor="w")

        self.output_text = scrolledtext.ScrolledText(
            log_section, font=("Consolas", 9),
            bg="white", fg="black", wrap=tk.WORD, height=12,
        )
        self.output_text.pack(fill="both", expand=True, pady=(6, 0))

        self._go_to_step(1)
        self._sync_default_ip_toggle()

    def _refresh_ip_status(self):
        """Update the IP status indicator label."""
        if hasattr(self, "ip_var"):
            self._ip_address = self.ip_var.get().strip()
        if self._ip_address:
            self._ip_status_label.config(
                text=f"\u2705  {self._ip_address}",
                fg=COLORS["success"],
            )
        else:
            self._ip_status_label.config(
                text="\u26a0  Not set \u2014 click \u2699 to configure",
                fg=COLORS["warning"],
            )
        self._update_next_button_state()

    def _toggle_use_default_ip(self):
        if not self._use_default_var.get():
            self._ip_entry_widget.configure(state="normal")
            self._update_next_button_state()
            return

        if not self._ip_address:
            self._use_default_var.set(False)
            self._ip_entry_widget.configure(state="normal")
            self._update_next_button_state()
            return

        if hasattr(self, "ip_var"):
            self.ip_var.set(self._ip_address)
        self._ip_entry_widget.configure(state="disabled")
        self._update_next_button_state()

    def _sync_default_ip_toggle(self):
        if not hasattr(self, "_use_default_var"):
            return
        if not self._ip_address:
            self._use_default_var.set(False)
            self._ip_entry_widget.configure(state="normal")
        elif self._use_default_var.get():
            if hasattr(self, "ip_var"):
                self.ip_var.set(self._ip_address)
            self._ip_entry_widget.configure(state="disabled")

    def _open_ip_settings(self):
        """Open a dialog to set, edit, or delete the default IP address."""
        from tkinter import messagebox

        dlg = tk.Toplevel(self.frame.winfo_toplevel())
        dlg.title("IP Address Settings")
        dlg.geometry("460x280")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.configure(bg=COLORS["bg_primary"])
        dlg.update_idletasks()
        x = (dlg.winfo_screenwidth() - 460) // 2
        y = (dlg.winfo_screenheight() - 280) // 2
        dlg.geometry(f"460x280+{x}+{y}")


        tk.Label(
            dlg, text="\u2699  IP Address Settings",
            font=("Segoe UI", 13, "bold"),
            bg=COLORS["bg_primary"], fg=COLORS["text_primary"],
        ).pack(pady=(16, 4))
        tk.Label(
            dlg,
            text="Default IP address assigned to new subdomains",
            font=("Segoe UI", 9),
            bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
        ).pack(pady=(0, 12))


        fields = tk.Frame(dlg, bg=COLORS["bg_primary"])
        fields.pack(fill="x", padx=24)

        tk.Label(
            fields, text="IP Address", anchor="w",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
        ).pack(fill="x", pady=(0, 2))

        ip_var = tk.StringVar(value=self._ip_address)
        ip_entry = tk.Entry(
            fields, textvariable=ip_var,
            font=("Segoe UI", 11), relief="flat",
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"],
        )
        ip_entry.pack(fill="x", ipady=6)

        tk.Label(
            fields,
            text="Saved in .env \u2014 used as default for new entries",
            anchor="w", font=("Segoe UI", 8),
            bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
        ).pack(fill="x", pady=(4, 0))


        btn_frame = tk.Frame(dlg, bg=COLORS["bg_primary"])
        btn_frame.pack(fill="x", padx=24, pady=(20, 12))

        def _save():
            val = ip_var.get().strip()
            if not val:
                messagebox.showwarning(
                    "Empty IP",
                    "Please enter an IP address or use Delete to remove it.",
                    parent=dlg,
                )
                return
            save_default_ip_address(val)
            self._ip_address = val
            if hasattr(self, "ip_var"):
                self.ip_var.set(val)
            self._refresh_ip_status()
            self._sync_default_ip_toggle()
            dlg.destroy()

        def _delete():
            if messagebox.askyesno(
                "Delete IP", "Remove the saved default IP address?", parent=dlg
            ):
                clear_default_ip_address()
                self._ip_address = ""
                if hasattr(self, "ip_var"):
                    self.ip_var.set("")
                self._refresh_ip_status()
                self._sync_default_ip_toggle()
                dlg.destroy()

        tk.Button(
            btn_frame, text="\U0001f4be  Save IP",
            font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
            bg=COLORS["success"], fg="white",
            activebackground=COLORS["success"],
            command=_save,
        ).pack(side="left", ipadx=12, ipady=6)

        tk.Button(
            btn_frame, text="\U0001f5d1  Delete IP",
            font=("Segoe UI", 10), relief="flat", cursor="hand2",
            bg=COLORS["error"], fg="white",
            activebackground=COLORS["error"],
            command=_delete,
        ).pack(side="left", padx=(10, 0), ipadx=12, ipady=6)

        tk.Button(
            btn_frame, text="Cancel",
            font=("Segoe UI", 10), relief="flat", cursor="hand2",
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
            command=dlg.destroy,
        ).pack(side="right", ipadx=12, ipady=6)


        dlg.bind("<Return>", lambda e: _save())
        dlg.bind("<Escape>", lambda e: dlg.destroy())

    def _update_domain_preview(self, event=None):
        """Update the full domain preview when user types subdomain."""
        subdomain = self.subdomain_entry.get().strip()
        if subdomain:
            full_domain = subdomain + self.dns_suffix
            self.domain_preview_label.config(
                text=f"Full domain: {full_domain}",
                fg=COLORS["success"]
            )
            if full_domain.lower() in self._known_domains:
                self.domain_availability_label.config(
                    text="Availability: Already exists",
                    fg=COLORS["warning"],
                )
            else:
                self.domain_availability_label.config(
                    text="Availability: Available (not yet existing)",
                    fg=COLORS["success"],
                )
        else:
            self.domain_preview_label.config(
                text="Full domain: (enter subdomain above)",
                fg=COLORS["text_secondary"]
            )
            self.domain_availability_label.config(
                text="Availability: Enter a subdomain to check",
                fg=COLORS["text_secondary"],
            )
        self._update_preview_summary()
        self._update_next_button_state()

    def set_known_domains(self, domains):
        """Set known domains used by availability note under subdomain input."""
        normalized = set()
        for d in domains or []:
            val = (d or "").strip().lower()
            if val:
                normalized.add(val)
        self._known_domains = normalized
        self._update_domain_preview()

    def _validate_step1(self):
        return bool(self.subdomain_entry.get().strip())

    def _validate_step2(self):
        return bool(self.ip_var.get().strip())

    def _update_preview_summary(self):
        domain = self.get_full_domain() or "—"
        ip = self.ip_var.get().strip() or "—"
        self._preview_domain_label.config(text=f"Domain: {domain}")
        self._preview_ip_label.config(text=f"Target IP: {ip}")

    def _update_add_button_state(self):
        if self._wizard_step == 3 and self._confirm_var.get():
            if not self.add_btn.winfo_ismapped():
                self.add_btn.pack(side="left", padx=(0, 8))
        else:
            if self.add_btn.winfo_ismapped():
                self.add_btn.pack_forget()

    def _update_progress_indicator(self):
        for idx, dot in enumerate(self._progress_dots, start=1):
            if idx == self._wizard_step:
                dot.config(bg=COLORS["accent"], fg="white")
            else:
                dot.config(bg=COLORS["bg_accent"], fg=COLORS["text_secondary"])

    def _update_next_button_state(self):
        if not hasattr(self, "next_step_btn"):
            return
        if self._wizard_step == 1:
            enabled = self._validate_step1()
        elif self._wizard_step == 2:
            enabled = self._validate_step2()
        else:
            enabled = False
        self.next_step_btn.configure(state="normal" if enabled else "disabled")

    def _on_next_step(self):
        if self._wizard_step == 1 and not self._validate_step1():
            self.log("Please enter a subdomain before continuing.", "warning")
            return
        if self._wizard_step == 2 and not self._validate_step2():
            self.log("Please confirm the target IP before continuing.", "warning")
            return
        self._go_to_step(self._wizard_step + 1)

    def _go_to_step(self, step):
        step = max(1, min(3, int(step)))
        self._wizard_step = step

        self.step1_frame.pack_forget()
        self.step2_frame.pack_forget()
        self.step3_frame.pack_forget()

        if step == 1:
            self._step_indicator_label.config(text="Step 1 of 3: Domain Input")
            self.step1_frame.pack(fill="x")
            self.prev_step_btn.configure(state="disabled")
            self.next_step_btn.configure(text="Next →")
            self._confirm_var.set(False)
        elif step == 2:
            self._step_indicator_label.config(text="Step 2 of 3: Target Server/IP Confirmation")
            self.step2_frame.pack(fill="x")
            self.prev_step_btn.configure(state="normal")
            self.next_step_btn.configure(text="Next →")
            self._confirm_var.set(False)
            self._refresh_ip_status()
        else:
            self._step_indicator_label.config(text="Step 3 of 3: Preview and Confirm")
            self.step3_frame.pack(fill="x")
            self.prev_step_btn.configure(state="normal")
            self.next_step_btn.configure(text="Next →")
            self._update_preview_summary()

        self._update_progress_indicator()
        self._update_next_button_state()
        self._update_add_button_state()

    def get_full_domain(self):
        """Get the full domain name with suffix."""
        subdomain = self.subdomain_entry.get().strip()
        if subdomain:
            return subdomain + self.dns_suffix
        return ""

    @property
    def ip_entry(self):
        """Return a mock entry-like object for compatibility."""
        return self

    def get(self):
        """Return the IP address."""
        if hasattr(self, "ip_var"):
            self._ip_address = self.ip_var.get().strip()
        return self._ip_address

    def delete(self, _start=None, _end=None):
        """Entry-like compatibility for controller reset calls."""
        if hasattr(self, "ip_var"):
            self.ip_var.set("")
        self._ip_address = ""
        self._refresh_ip_status()
        self._confirm_var.set(False)
        self._go_to_step(1)

    def insert(self, _index, value):
        """Entry-like compatibility for controller writes."""
        val = (value or "").strip()
        if hasattr(self, "ip_var"):
            self.ip_var.set(val)
        self._ip_address = val
        self._refresh_ip_status()


    def log(self, message, tag="info"):
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)

    def clear_log(self):
        self.output_text.delete(1.0, tk.END)

    def show(self):
        self.frame.pack(fill="both", expand=True)

    def hide(self):
        self.frame.pack_forget()
