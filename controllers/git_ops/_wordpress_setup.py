"""WordPress setup tools — config generation, database, permissions, vhost, installer."""
import os
from tkinter import messagebox

from models.config import COLORS


class WordPressSetupMixin:
    """Methods for WordPress configuration, database, permissions, vhost, and installer."""


    def wp_generate_config(self, subdomain=None, db_config=None, log_fn=None):
        """Generate wp-config.php with DB credentials and salt keys."""
        if subdomain is None:
            subdomain = self._validate_subdomain_selected()
            if not subdomain:
                return
            if not self._require_git_initialized():
                return

        db_cfg = db_config if db_config is not None else self.view.repo_setup_page.get_wp_db_config()
        if not db_cfg["db_name"]:
            messagebox.showwarning("Missing Info", "Please fill in the Database Name.")
            return

        _log = log_fn if log_fn is not None else self.view.repo_setup_page.log

        def _worker():
            client = None
            try:
                _log(f"\n{'=' * 50}")
                _log("Generating wp-config.php...")
                self.view.status_var.set("Generating wp-config.php...")
                client = self.ssh.connect()
                if not client:
                    _log("ERROR: SSH connection failed.")
                    return

                path = self.git_manager.get_subdomain_path(subdomain)


                check = f"test -f '{path}/wp-config-sample.php' && echo 'YES' || echo 'NO'"
                _, stdout, _ = client.exec_command(check)
                has_sample = stdout.read().decode().strip() == "YES"

                if has_sample:
                    _log("Found wp-config-sample.php — using as base")
                    cmd = f"cp '{path}/wp-config-sample.php' '{path}/wp-config.php'"
                    _, stdout, _ = client.exec_command(cmd)
                    stdout.read()
                else:
                    _log("No sample found — downloading fresh wp-config-sample.php")
                    cmd = (
                        f"cd '{path}' && "
                        f"curl -sO https://raw.githubusercontent.com/WordPress/WordPress/master/wp-config-sample.php && "
                        f"cp wp-config-sample.php wp-config.php"
                    )
                    _, stdout, _ = client.exec_command(cmd)
                    stdout.read()


                replacements = [
                    ("database_name_here", db_cfg["db_name"]),
                    ("username_here", db_cfg["db_user"]),
                    ("password_here", db_cfg["db_pass"]),
                    ("localhost", db_cfg["db_host"]),
                ]
                for old, new in replacements:
                    sed_cmd = f"sed -i \"s/{old}/{new}/g\" '{path}/wp-config.php'"
                    _, stdout, _ = client.exec_command(sed_cmd)
                    stdout.read()
                _log(f"  DB: {db_cfg['db_name']}  User: {db_cfg['db_user']}  Host: {db_cfg['db_host']}")


                _log("Fetching unique salt keys from WordPress.org...")
                salt_cmd = (
                    f"SALTS=$(curl -s https://api.wordpress.org/secret-key/1.1/salt/) && "
                    f"sed -i '/AUTH_KEY/d;/SECURE_AUTH_KEY/d;/LOGGED_IN_KEY/d;/NONCE_KEY/d;"
                    f"/AUTH_SALT/d;/SECURE_AUTH_SALT/d;/LOGGED_IN_SALT/d;/NONCE_SALT/d' "
                    f"'{path}/wp-config.php' && "
                    f"echo \"$SALTS\" >> '{path}/wp-config.php'"
                )
                _, stdout, _ = client.exec_command(salt_cmd)
                stdout.read()
                _log("Salt keys generated and injected.")


                perm_cmd = f"chmod 600 '{path}/wp-config.php'"
                _, stdout, _ = client.exec_command(perm_cmd)
                stdout.read()

                _log("\u2713  wp-config.php created successfully!")
                self.view.status_var.set("wp-config.php generated")
                self._record_app_activity(subdomain, "wp-config", f"Generated wp-config.php for {subdomain}")

            except Exception as e:
                _log(f"ERROR: {e}")
                self.view.status_var.set(f"Error: {e}")
            finally:
                if client:
                    client.close()

        self.submit_background_job(
            "WordPress Generate Config",
            _worker,
            dedupe_key=f"wp_config:{subdomain}",
            source="git",
        )

    def wp_check_database(self, subdomain=None, db_config=None, log_fn=None):
        """Check if the WordPress database exists; create it if missing."""
        if subdomain is None:
            subdomain = self._validate_subdomain_selected()
            if not subdomain:
                return

        db_cfg = db_config if db_config is not None else self.view.repo_setup_page.get_wp_db_config()
        if not db_cfg["db_name"]:
            messagebox.showwarning("Missing Info", "Please fill in the Database Name.")
            return

        _log = log_fn if log_fn is not None else self.view.repo_setup_page.log

        def _worker():
            client = None
            try:
                _log(f"\n{'=' * 50}")
                _log(f"Checking database '{db_cfg['db_name']}'...")
                self.view.status_var.set("Checking MySQL database...")
                client = self.ssh.connect()
                if not client:
                    _log("ERROR: SSH connection failed.")
                    return


                auth = f"-u '{db_cfg['db_user']}'"
                if db_cfg["db_pass"]:
                    auth += f" -p'{db_cfg['db_pass']}'"
                if db_cfg["db_host"] != "localhost":
                    auth += f" -h '{db_cfg['db_host']}'"


                check_cmd = f"mysql {auth} -e \"SHOW DATABASES LIKE '{db_cfg['db_name']}'\" 2>&1"
                _, stdout, _ = client.exec_command(check_cmd)
                output = stdout.read().decode().strip()

                if db_cfg["db_name"] in output:
                    _log(f"\u2713  Database '{db_cfg['db_name']}' exists!")

                    tbl_cmd = f"mysql {auth} -e \"USE {db_cfg['db_name']}; SHOW TABLES;\" 2>&1"
                    _, stdout, _ = client.exec_command(tbl_cmd)
                    tables = stdout.read().decode().strip()
                    tbl_count = max(0, len(tables.splitlines()) - 1)
                    _log(f"  Tables found: {tbl_count}")
                    self.view.status_var.set(f"Database exists ({tbl_count} tables)")
                elif "Access denied" in output or "ERROR" in output:
                    _log(f"ERROR: {output}")
                    self.view.status_var.set("Database check failed")
                else:
                    _log(f"Database '{db_cfg['db_name']}' not found — creating...")
                    create_cmd = (
                        f"mysql {auth} -e \""
                        f"CREATE DATABASE \\`{db_cfg['db_name']}\\` "
                        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\" 2>&1"
                    )
                    _, stdout, _ = client.exec_command(create_cmd)
                    result = stdout.read().decode().strip()
                    if result and "ERROR" in result:
                        _log(f"ERROR creating DB: {result}")
                        self.view.status_var.set("Failed to create database")
                    else:
                        _log(f"\u2713  Database '{db_cfg['db_name']}' created!")
                        self.view.status_var.set("Database created")
                        self._record_app_activity(subdomain, "wp-db", f"Created MySQL DB: {db_cfg['db_name']}")

            except Exception as e:
                _log(f"ERROR: {e}")
                self.view.status_var.set(f"Error: {e}")
            finally:
                if client:
                    client.close()

        self.submit_background_job(
            "WordPress Check DB",
            _worker,
            dedupe_key=f"wp_db_check:{subdomain}",
            source="git",
        )

    def _upload_and_import_sql(self, subdomain, db_config, log_fn, activity_tag):
        """Shared helper: upload a local SQL file via SFTP and import into MySQL.

        Used by both wp_upload_sql and vite_upload_sql.
        """
        from tkinter import messagebox
        db_cfg = db_config

        if not db_cfg.get("db_name"):
            messagebox.showwarning("Missing Info", "Please fill in the Database Name.")
            return
        if not db_cfg.get("db_user"):
            messagebox.showwarning("Missing Info", "Please fill in the Database User.")
            return
        if not db_cfg.get("sql_path"):
            messagebox.showwarning("No SQL File", "Please select a SQL file to upload.")
            return

        sql_local = db_cfg["sql_path"]
        if not os.path.isfile(sql_local):
            messagebox.showerror("File Not Found", f"Cannot find:\n{sql_local}")
            return

        _log = log_fn if log_fn is not None else self.view.repo_setup_page.log

        def _worker():
            client = None
            remote_sql = None
            try:
                _log(f"\n{'=' * 50}")
                _log("Uploading SQL file to server...")
                self.view.status_var.set("Uploading SQL file...")
                client = self.ssh.connect()
                if not client:
                    _log("ERROR: SSH connection failed.")
                    return

                remote_sql = f"/tmp/{os.path.basename(sql_local)}"
                sftp = client.open_sftp()
                try:
                    sftp.put(sql_local, remote_sql)
                finally:
                    sftp.close()
                _log(f"\u2713  Uploaded to {remote_sql}")

                auth = f"-u '{db_cfg['db_user']}'"
                if db_cfg.get("db_pass"):
                    auth += f" -p'{db_cfg['db_pass']}'"
                if db_cfg.get("db_host", "localhost") != "localhost":
                    auth += f" -h '{db_cfg['db_host']}'"


                ensure_cmd = (
                    f"mysql {auth} -e \""
                    f"CREATE DATABASE IF NOT EXISTS \\`{db_cfg['db_name']}\\` "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\" 2>&1"
                )
                _, stdout, _ = client.exec_command(ensure_cmd)
                result = stdout.read().decode().strip()
                if result and "ERROR" in result:
                    _log(f"ERROR ensuring database: {result}")
                    self.view.status_var.set("Import failed — DB error")
                    return

                _log(f"Importing into '{db_cfg['db_name']}'...")
                self.view.status_var.set("Importing SQL...")
                import_cmd = f"mysql {auth} '{db_cfg['db_name']}' < '{remote_sql}' 2>&1"
                _, stdout, _ = client.exec_command(import_cmd)
                import_out = stdout.read().decode().strip()

                if import_out and "ERROR" in import_out:
                    _log(f"ERROR during import:\n{import_out}")
                    self.view.status_var.set("SQL import failed")
                else:
                    if import_out:
                        _log(f"  {import_out}")
                    _log(f"\u2713  SQL imported into '{db_cfg['db_name']}' successfully!")
                    self.view.status_var.set("SQL imported successfully")
                    self._record_app_activity(subdomain, activity_tag,
                                              f"Imported SQL into {db_cfg['db_name']}")

            except Exception as e:
                _log(f"ERROR: {e}")
                self.view.status_var.set(f"Error: {e}")
            finally:

                if client and remote_sql:
                    try:
                        client.exec_command(f"rm -f '{remote_sql}'")
                    except Exception:
                        pass
                if client:
                    client.close()

        self.submit_background_job(
            "Upload SQL Import",
            _worker,
            dedupe_key=f"sql_import:{subdomain}",
            source="git",
        )

    def wp_upload_sql(self, subdomain=None, db_config=None, log_fn=None):
        """Upload a local SQL file to the server via SFTP and import it into WordPress database."""
        if subdomain is None:
            subdomain = self._validate_subdomain_selected()
            if not subdomain:
                return
        db_cfg = db_config if db_config is not None else self.view.repo_setup_page.get_wp_db_config()
        self._upload_and_import_sql(subdomain, db_cfg, log_fn, "wp-db")

    def wp_fix_permissions(self, subdomain=None, db_config=None, log_fn=None):
        """Fix WordPress file and directory permissions."""
        if subdomain is None:
            subdomain = self._validate_subdomain_selected()
            if not subdomain:
                return

        _log = log_fn if log_fn is not None else self.view.repo_setup_page.log

        def _worker():
            client = None
            try:
                _log(f"\n{'=' * 50}")
                _log(f"Fixing WordPress permissions for {subdomain}...")
                self.view.status_var.set("Fixing permissions...")
                client = self.ssh.connect()
                if not client:
                    _log("ERROR: SSH connection failed.")
                    return

                path = self.git_manager.get_subdomain_path(subdomain)
                fw_ok, fw_msg = self.git_manager.install_wordpress(client, subdomain, _log)
                _log(fw_msg)

                _log("\u2713  Permissions fixed!")
                self.view.status_var.set("Permissions updated")
                self._record_app_activity(subdomain, "wp-perms", f"Fixed WP permissions for {subdomain}")

            except Exception as e:
                _log(f"ERROR: {e}")
                self.view.status_var.set(f"Error: {e}")
            finally:
                if client:
                    client.close()

        self.submit_background_job(
            "WordPress Fix Permissions",
            _worker,
            dedupe_key=f"wp_perms:{subdomain}",
            source="git",
        )

    def wp_fix_vhost(self, subdomain=None, db_config=None, log_fn=None):
        """Fix Apache vhost to enable AllowOverride All and create SSL vhost if missing."""
        if subdomain is None:
            subdomain = self._validate_subdomain_selected()
            if not subdomain:
                return

        _log = log_fn if log_fn is not None else self.view.repo_setup_page.log

        def _worker():
            client = None
            try:
                _log(f"\n{'=' * 50}")
                _log(f"Fixing Apache vhost for {subdomain}...")
                self.view.status_var.set("Fixing Apache vhost...")
                client = self.ssh.connect()
                if not client:
                    _log("ERROR: SSH connection failed.")
                    return

                path = self.git_manager.get_subdomain_path(subdomain)
                vhost_name = subdomain.replace("/", "")
                vhost_path = f"/etc/apache2/sites-available/{vhost_name}.conf"
                ssl_vhost_path = f"/etc/apache2/sites-available/{vhost_name}-le-ssl.conf"


                check = f"test -f '{vhost_path}' && echo 'YES' || echo 'NO'"
                _, stdout, _ = client.exec_command(check)
                http_exists = stdout.read().decode().strip() == "YES"

                if not http_exists:
                    _log(f"Creating HTTP vhost at {vhost_path}...")
                    http_vhost = f'''<VirtualHost *:80>
    ServerName {subdomain}
    DocumentRoot {path}

    <Directory {path}>
        AllowOverride All
        Require all granted
    </Directory>

    ErrorLog ${{APACHE_LOG_DIR}}/error.log
    CustomLog ${{APACHE_LOG_DIR}}/access.log combined
</VirtualHost>'''
                    create_cmd = f"echo '{http_vhost}' > '{vhost_path}'"
                    _, stdout, _ = client.exec_command(create_cmd)
                    stdout.read()
                    _log("HTTP vhost created.")
                else:
                    _log("HTTP vhost exists.")

                    sed_cmd = f"sed -i 's|AllowOverride.*|AllowOverride All|g' '{vhost_path}'"
                    _, stdout, _ = client.exec_command(sed_cmd)
                    stdout.read()


                check_ssl = f"test -f '{ssl_vhost_path}' && echo 'YES' || echo 'NO'"
                _, stdout, _ = client.exec_command(check_ssl)
                ssl_exists = stdout.read().decode().strip() == "YES"


                check_443 = f"grep -q ':443' '{vhost_path}' && echo 'YES' || echo 'NO'"
                _, stdout, _ = client.exec_command(check_443)
                has_443 = stdout.read().decode().strip() == "YES"

                if not ssl_exists and not has_443:
                    _log("SSL vhost missing! Checking for SSL certificate...")


                    cert_path = f"/etc/letsencrypt/live/{subdomain}/fullchain.pem"
                    check_cert = f"test -f '{cert_path}' && echo 'YES' || echo 'NO'"
                    _, stdout, _ = client.exec_command(check_cert)
                    cert_exists = stdout.read().decode().strip() == "YES"

                    if cert_exists:
                        _log("SSL certificate found! Creating SSL vhost...")
                        ssl_vhost = f'''<VirtualHost *:443>
    ServerName {subdomain}
    DocumentRoot {path}

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/{subdomain}/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/{subdomain}/privkey.pem

    <Directory {path}>
        AllowOverride All
        Require all granted
    </Directory>

    ErrorLog ${{APACHE_LOG_DIR}}/error.log
    CustomLog ${{APACHE_LOG_DIR}}/access.log combined
</VirtualHost>'''
                        create_ssl = f"echo '{ssl_vhost}' > '{ssl_vhost_path}'"
                        _, stdout, _ = client.exec_command(create_ssl)
                        stdout.read()
                        _log(f"SSL vhost created at {ssl_vhost_path}")


                        enable_ssl = f"a2ensite {vhost_name}-le-ssl.conf 2>&1"
                        _, stdout, _ = client.exec_command(enable_ssl)
                        _log(f"  {stdout.read().decode().strip()}")
                    else:
                        _log("SSL certificate not found. Running Certbot...")
                        _log("(This may take a minute...)")
                        certbot_cmd = f"certbot --apache -d {subdomain} --non-interactive --agree-tos --email admin@{subdomain.split('.')[-2]}.{subdomain.split('.')[-1]} 2>&1"
                        _, stdout, _ = client.exec_command(certbot_cmd, timeout=120)
                        certbot_out = stdout.read().decode().strip()
                        for line in certbot_out.split('\n')[-10:]:
                            _log(f"  {line}")

                        if "Congratulations" in certbot_out or "Successfully" in certbot_out:
                            _log("\u2713 SSL certificate installed!")
                        else:
                            _log("\u26a0 Certbot may have failed. Check output above.")
                else:
                    _log("SSL vhost already exists.")

                    if ssl_exists:
                        sed_ssl = f"sed -i 's|AllowOverride.*|AllowOverride All|g' '{ssl_vhost_path}'"
                        _, stdout, _ = client.exec_command(sed_ssl)
                        stdout.read()


                _log("Enabling sites...")
                enable_cmd = f"a2ensite {vhost_name}.conf 2>&1"
                _, stdout, _ = client.exec_command(enable_cmd)
                stdout.read()


                _log("Enabling Apache modules...")
                mods_cmd = "a2enmod rewrite ssl 2>/dev/null"
                _, stdout, _ = client.exec_command(mods_cmd)
                stdout.read()


                ht_check = f"test -f '{path}/.htaccess' && echo 'YES' || echo 'NO'"
                _, stdout, _ = client.exec_command(ht_check)
                has_ht = stdout.read().decode().strip() == "YES"

                if not has_ht:
                    _log("Creating WordPress .htaccess...")
                    htaccess = (
                        "# BEGIN WordPress\\n"
                        "<IfModule mod_rewrite.c>\\n"
                        "RewriteEngine On\\n"
                        "RewriteBase /\\n"
                        "RewriteRule ^index\\\\.php$ - [L]\\n"
                        "RewriteCond %{REQUEST_FILENAME} !-f\\n"
                        "RewriteCond %{REQUEST_FILENAME} !-d\\n"
                        "RewriteRule . /index.php [L]\\n"
                        "</IfModule>\\n"
                        "# END WordPress"
                    )
                    ht_cmd = f"echo -e '{htaccess}' > '{path}/.htaccess' && chmod 644 '{path}/.htaccess'"
                    _, stdout, _ = client.exec_command(ht_cmd)
                    stdout.read()
                    _log(".htaccess created.")


                _log("Restarting Apache...")
                restart_cmd = "systemctl restart apache2 2>&1"
                _, stdout, _ = client.exec_command(restart_cmd)
                restart_out = stdout.read().decode().strip()
                if restart_out:
                    _log(f"  {restart_out}")


                status_cmd = "systemctl is-active apache2"
                _, stdout, _ = client.exec_command(status_cmd)
                status = stdout.read().decode().strip()

                if status == "active":
                    _log(f"\n{'=' * 50}")
                    _log("\u2713  Apache vhost configured successfully!")
                    _log(f"   Visit: https://{subdomain}/")
                    _log(f"{'=' * 50}")
                    self.view.status_var.set("Apache vhost fixed!")
                else:
                    _log(f"\u26a0 Apache status: {status}")
                    self.view.status_var.set(f"Apache: {status}")

                self._record_app_activity(subdomain, "wp-vhost", f"Fixed Apache vhost for {subdomain}")

            except Exception as e:
                _log(f"ERROR: {e}")
                self.view.status_var.set(f"Error: {e}")
            finally:
                if client:
                    client.close()

        self.submit_background_job(
            "WordPress Fix Vhost",
            _worker,
            dedupe_key=f"wp_vhost:{subdomain}",
            source="git",
        )

    def wp_run_installer(self, subdomain=None, db_config=None, install_config=None, log_fn=None):
        """Run WP-CLI core install to populate all WordPress database tables."""
        if subdomain is None:
            subdomain = self._validate_subdomain_selected()
            if not subdomain:
                return

        db_cfg   = db_config      if db_config      is not None else self.view.repo_setup_page.get_wp_db_config()
        inst_cfg = install_config if install_config is not None else self.view.repo_setup_page.get_wp_install_config()

        if not db_cfg["db_name"]:
            messagebox.showwarning("Missing Info", "Please fill in the Database Name first.")
            return
        if not inst_cfg["admin_user"]:
            messagebox.showwarning("Missing Info", "Please fill in the Admin User.")
            return
        if not inst_cfg["admin_pass"]:
            messagebox.showwarning("Missing Info", "Please fill in the Admin Password.")
            return
        if not inst_cfg["admin_email"]:
            messagebox.showwarning("Missing Info", "Please fill in the Admin Email.")
            return

        _log = log_fn if log_fn is not None else self.view.repo_setup_page.log
        site_url = f"http://{subdomain}"

        def _worker():
            client = None
            try:
                _log(f"\n{'=' * 50}")
                _log("Running WordPress installer via WP-CLI...")
                self.view.status_var.set("Running WP installer...")
                client = self.ssh.connect()
                if not client:
                    _log("ERROR: SSH connection failed.")
                    return

                path = self.git_manager.get_subdomain_path(subdomain)


                _log("Checking for WP-CLI...")
                _, stdout, _ = client.exec_command("which wp 2>/dev/null")
                wp_bin = stdout.read().decode().strip()

                if not wp_bin:
                    _log("WP-CLI not found — downloading to /usr/local/bin/wp...")
                    dl_cmd = (
                        "curl -sO https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar && "
                        "chmod +x wp-cli.phar && mv wp-cli.phar /usr/local/bin/wp"
                    )
                    _, stdout, stderr = client.exec_command(dl_cmd)
                    stdout.read()
                    err = stderr.read().decode().strip()
                    _, stdout, _ = client.exec_command("which wp 2>/dev/null")
                    wp_bin = stdout.read().decode().strip()
                    if not wp_bin:
                        _log(f"ERROR: Could not install WP-CLI. {err}")
                        self.view.status_var.set("WP-CLI install failed")
                        return
                    _log("WP-CLI installed successfully.")
                else:
                    _log(f"WP-CLI found at: {wp_bin}")


                _log("Checking installation status...")
                check_cmd = f"wp core is-installed --path='{path}' --allow-root 2>&1; echo \"EXIT:$?\""
                _, stdout, _ = client.exec_command(check_cmd)
                check_out = stdout.read().decode().strip()
                if "EXIT:0" in check_out:
                    _log("\u26a0  WordPress is already installed — tables already exist.")
                    _log(f"  Admin URL: {site_url}/wp-admin")
                    self.view.status_var.set("Already installed")
                    return


                title = inst_cfg["site_title"] or "My WordPress Site"
                _log(f"Installing WordPress...")
                _log(f"  URL:   {site_url}")
                _log(f"  Title: {title}")
                _log(f"  Admin: {inst_cfg['admin_user']}")

                install_cmd = (
                    f"wp core install "
                    f"--url='{site_url}' "
                    f"--title='{title}' "
                    f"--admin_user='{inst_cfg['admin_user']}' "
                    f"--admin_password='{inst_cfg['admin_pass']}' "
                    f"--admin_email='{inst_cfg['admin_email']}' "
                    f"--path='{path}' "
                    f"--allow-root 2>&1"
                )
                _, stdout, _ = client.exec_command(install_cmd)
                result = stdout.read().decode().strip()

                if "Success" in result or "success" in result:
                    _log(f"\u2713  WordPress installed successfully!")
                    _log(f"  Admin URL:  {site_url}/wp-admin")
                    _log(f"  Username:   {inst_cfg['admin_user']}")
                    _log(f"  (Check email for password confirmation)")
                    self.view.status_var.set("WordPress installed!")
                    self._record_app_activity(subdomain, "wp-install",
                                              f"WordPress installed via WP-CLI for {subdomain}")
                elif "Error" in result or "ERROR" in result:
                    _log(f"ERROR: {result}")
                    self.view.status_var.set("WP install failed")
                else:
                    _log(f"Result: {result}")
                    _log("WP installer ran — verify tables in MySQL Databases browser.")
                    self.view.status_var.set("WP installer ran")

            except Exception as e:
                _log(f"ERROR: {e}")
                self.view.status_var.set(f"Error: {e}")
            finally:
                if client:
                    client.close()

        self.submit_background_job(
            "WordPress Run Installer",
            _worker,
            dedupe_key=f"wp_install:{subdomain}",
            source="git",
        )
