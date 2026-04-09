"""Vite database helpers — .env generation, database creation, SQL upload."""
from tkinter import messagebox


class ViteSetupMixin:
    """Methods for Vite project database configuration."""


    def vite_generate_env(self, subdomain=None, db_config=None, log_fn=None):
        """Generate a .env file with DB credentials in the Vite project folder on the server."""
        if subdomain is None:
            subdomain = self._validate_subdomain_selected()
            if not subdomain:
                return

        db_cfg = db_config if db_config is not None else self.view.repo_setup_page.get_vite_db_config()
        if not db_cfg.get("db_name"):
            from tkinter import messagebox
            messagebox.showwarning("Missing Info", "Please fill in the Database Name.")
            return

        _log = log_fn if log_fn is not None else self.view.repo_setup_page.log

        def _worker():
            client = None
            try:
                _log(f"\n{'=' * 50}")
                _log("Generating .env with database credentials...")
                self.view.status_var.set("Generating .env file...")
                client = self.ssh.connect()
                if not client:
                    _log("ERROR: SSH connection failed.")
                    return

                path = self.git_manager.get_subdomain_path(subdomain)

                env_content = (
                    f"DB_HOST={db_cfg.get('db_host', 'localhost')}\n"
                    f"DB_PORT=3306\n"
                    f"DB_DATABASE={db_cfg['db_name']}\n"
                    f"DB_USERNAME={db_cfg.get('db_user', 'root')}\n"
                    f"DB_PASSWORD={db_cfg.get('db_pass', '')}\n"
                )


                check_cmd = f"test -f '{path}/.env' && echo 'YES' || echo 'NO'"
                _, stdout, _ = client.exec_command(check_cmd)
                env_exists = stdout.read().decode().strip() == "YES"

                if env_exists:

                    _log(".env exists — updating DB credentials...")
                    strip_cmd = (
                        f"sed -i '/^DB_HOST=/d;/^DB_PORT=/d;/^DB_DATABASE=/d;"
                        f"/^DB_USERNAME=/d;/^DB_PASSWORD=/d' '{path}/.env'"
                    )
                    _, stdout, _ = client.exec_command(strip_cmd)
                    stdout.read()

                    for line in env_content.strip().split('\n'):
                        append_cmd = f"echo '{line}' >> '{path}/.env'"
                        _, stdout, _ = client.exec_command(append_cmd)
                        stdout.read()
                else:
                    _log("Creating new .env file...")
                    write_cmd = f"cat > '{path}/.env' << 'ENVEOF'\n{env_content}ENVEOF"
                    _, stdout, _ = client.exec_command(write_cmd)
                    stdout.read()


                _, stdout, _ = client.exec_command(f"chmod 640 '{path}/.env'")
                stdout.read()


                gi_cmd = (
                    f"cd '{path}' && "
                    f"(test -f .gitignore && grep -q '\\.env' .gitignore) || "
                    f"echo '.env' >> .gitignore"
                )
                _, stdout, _ = client.exec_command(gi_cmd)
                stdout.read()

                _log(f"  DB_DATABASE={db_cfg['db_name']}")
                _log(f"  DB_USERNAME={db_cfg.get('db_user', 'root')}")
                _log(f"  DB_HOST={db_cfg.get('db_host', 'localhost')}")
                _log(f"\u2713  .env saved to {path}/.env")
                _log("  (also added .env to .gitignore)")
                self.view.status_var.set(".env file saved on server")
                self._record_app_activity(subdomain, "vite-env",
                                          f"Generated .env for {subdomain}")

            except Exception as e:
                _log(f"ERROR: {e}")
                self.view.status_var.set(f"Error: {e}")
            finally:
                if client:
                    client.close()

        self.submit_background_job(
            "Vite Generate .env",
            _worker,
            dedupe_key=f"vite_env:{subdomain}",
            source="git",
        )

    def vite_create_db(self, subdomain=None, db_config=None, log_fn=None):
        """Create the MySQL database declared in the Vite DB config (if it doesn't exist)."""
        if subdomain is None:
            subdomain = self._validate_subdomain_selected()
            if not subdomain:
                return

        db_cfg = db_config if db_config is not None else self.view.repo_setup_page.get_vite_db_config()
        if not db_cfg.get("db_name"):
            from tkinter import messagebox
            messagebox.showwarning("Missing Info", "Please fill in the Database Name.")
            return

        _log = log_fn if log_fn is not None else self.view.repo_setup_page.log

        def _worker():
            client = None
            try:
                _log(f"\n{'=' * 50}")
                _log(f"Checking/creating database '{db_cfg['db_name']}'...")
                self.view.status_var.set("Checking MySQL database...")
                client = self.ssh.connect()
                if not client:
                    _log("ERROR: SSH connection failed.")
                    return

                auth = f"-u '{db_cfg['db_user']}'"
                if db_cfg.get("db_pass"):
                    auth += f" -p'{db_cfg['db_pass']}'"
                if db_cfg.get("db_host", "localhost") != "localhost":
                    auth += f" -h '{db_cfg['db_host']}'"

                check_cmd = f"mysql {auth} -e \"SHOW DATABASES LIKE '{db_cfg['db_name']}'\" 2>&1"
                _, stdout, _ = client.exec_command(check_cmd)
                output = stdout.read().decode().strip()

                if db_cfg["db_name"] in output:
                    tbl_cmd = f"mysql {auth} -e \"USE `{db_cfg['db_name']}`; SHOW TABLES;\" 2>&1"
                    _, stdout, _ = client.exec_command(tbl_cmd)
                    tables = stdout.read().decode().strip()
                    tbl_count = max(0, len(tables.splitlines()) - 1)
                    _log(f"\u2713  Database '{db_cfg['db_name']}' already exists ({tbl_count} tables)")
                    self.view.status_var.set(f"Database exists ({tbl_count} tables)")
                elif "Access denied" in output or "ERROR" in output:
                    _log(f"ERROR: {output}")
                    self.view.status_var.set("Database check failed")
                else:
                    create_cmd = (
                        f"mysql {auth} -e \""
                        f"CREATE DATABASE \\`{db_cfg['db_name']}\\` "
                        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\" 2>&1"
                    )
                    _, stdout, _ = client.exec_command(create_cmd)
                    result = stdout.read().decode().strip()
                    if result and "ERROR" in result:
                        _log(f"ERROR creating database: {result}")
                        self.view.status_var.set("Failed to create database")
                    else:
                        _log(f"\u2713  Database '{db_cfg['db_name']}' created!")
                        self.view.status_var.set("Database created")
                        self._record_app_activity(subdomain, "vite-db",
                                                  f"Created MySQL DB: {db_cfg['db_name']}")

            except Exception as e:
                _log(f"ERROR: {e}")
                self.view.status_var.set(f"Error: {e}")
            finally:
                if client:
                    client.close()

        self.submit_background_job(
            "Vite Create DB",
            _worker,
            dedupe_key=f"vite_db:{subdomain}",
            source="git",
        )

    def vite_upload_sql(self, subdomain=None, db_config=None, log_fn=None):
        """Upload a local SQL file to the server via SFTP and import it into MySQL."""
        if subdomain is None:
            subdomain = self._validate_subdomain_selected()
            if not subdomain:
                return
        db_cfg = db_config if db_config is not None else self.view.repo_setup_page.get_vite_db_config()
        self._upload_and_import_sql(subdomain, db_cfg, log_fn, "vite-db")
