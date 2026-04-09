"""
Git Deployment Operations Mixin — Vite/WordPress installation,
remote directory cleaning, and SFTP upload.
"""
from typing import Callable, Optional, Tuple, List


class GitDeployOpsMixin:
    """Methods for deploying projects and uploading files to the server."""

    def install_vite(
        self,
        client,
        subdomain: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[bool, str]:
        """Install Vite in the subdomain folder.
        If package.json already exists, just run npm install.
        Otherwise, scaffold a new Vite project."""
        path = self.get_subdomain_path(subdomain)


        check_cmd = f"test -f '{path}/package.json' && echo 'EXISTS' || echo 'NO'"
        _, stdout, _ = client.exec_command(check_cmd)
        has_package_json = stdout.read().decode().strip() == 'EXISTS'

        if has_package_json:
            if log_callback:
                log_callback("package.json found — installing dependencies only...")
        else:
            if log_callback:
                log_callback("No package.json — creating new Vite project...")
            cmd = f"cd '{path}' && npm create vite@latest . -- --template vanilla -y 2>&1"
            _, stdout, _ = client.exec_command(cmd)
            output = stdout.read().decode().strip()
            if log_callback and output:
                for line in output.split('\n')[:10]:
                    log_callback(line)


        if log_callback:
            log_callback("Running npm install...")
        npm_cmd = f"cd '{path}' && npm install 2>&1"
        _, stdout, _ = client.exec_command(npm_cmd)
        npm_output = stdout.read().decode().strip()
        if log_callback and npm_output:
            for line in npm_output.split('\n')[-8:]:
                if line.strip():
                    log_callback(f"  {line.strip()}")


        check_nm = f"test -d '{path}/node_modules' && echo 'OK' || echo 'MISSING'"
        _, stdout, _ = client.exec_command(check_nm)
        nm_exists = stdout.read().decode().strip() == 'OK'

        if nm_exists:

            count_cmd = f"ls -d '{path}/node_modules'/*/ 2>/dev/null | wc -l"
            _, stdout, _ = client.exec_command(count_cmd)
            pkg_count = stdout.read().decode().strip()
            if log_callback:
                log_callback(f"node_modules installed ({pkg_count} packages)")
        else:
            if log_callback:
                log_callback("WARNING: node_modules not created")


        check_vite = f"grep -q 'vite' '{path}/package.json' 2>/dev/null && echo 'YES' || echo 'NO'"
        _, stdout, _ = client.exec_command(check_vite)
        is_vite = stdout.read().decode().strip() == 'YES'

        if is_vite:
            if log_callback:
                log_callback("Running npm run build...")
            build_cmd = f"cd '{path}' && npm run build 2>&1"
            _, stdout, _ = client.exec_command(build_cmd)
            build_out = stdout.read().decode().strip()
            if log_callback and build_out:
                for line in build_out.split('\n')[-5:]:
                    if line.strip():
                        log_callback(f"  {line.strip()}")

            check_dist = f"test -d '{path}/dist' && echo 'OK' || echo 'NO'"
            _, stdout, _ = client.exec_command(check_dist)
            if stdout.read().decode().strip() == 'OK':
                if log_callback:
                    log_callback("Build complete — dist/ folder created")


                if log_callback:
                    log_callback("Copying dist/ contents to document root...")
                copy_cmd = f"cp -rf {path}/dist/* {path}/ 2>&1"
                _, stdout, _ = client.exec_command(copy_cmd)
                copy_out = stdout.read().decode().strip()
                if log_callback:
                    if copy_out:
                        log_callback(f"  cp output: {copy_out}")
                    log_callback("Built files copied to document root.")


                verify_cmd = f"head -5 '{path}/index.html' 2>&1"
                _, stdout, _ = client.exec_command(verify_cmd)
                head_out = stdout.read().decode().strip()
                if log_callback:
                    log_callback(f"Root index.html preview:")
                    for line in head_out.split('\n')[:3]:
                        log_callback(f"  {line}")


                vhost_name = subdomain.replace('/', '')
                vhost_path = f"/etc/apache2/sites-available/{vhost_name}.conf"
                if log_callback:
                    log_callback(f"Checking vhost at {vhost_path}...")
                check_vhost = f"test -f '{vhost_path}' && echo 'YES' || echo 'NO'"
                _, stdout, _ = client.exec_command(check_vhost)
                vhost_exists = stdout.read().decode().strip() == 'YES'

                if vhost_exists:

                    check_ao = f"grep -q 'AllowOverride All' '{vhost_path}' && echo 'YES' || echo 'NO'"
                    _, stdout, _ = client.exec_command(check_ao)
                    if stdout.read().decode().strip() != 'YES':
                        if log_callback:
                            log_callback("Setting AllowOverride All in vhost...")
                        ao_cmd = f"sed -i 's|AllowOverride.*|AllowOverride All|g' '{vhost_path}' 2>/dev/null"
                        _, stdout, _ = client.exec_command(ao_cmd)
                        stdout.read()


                    check_dr = f"grep -q 'public_html/dist' '{vhost_path}' && echo 'YES' || echo 'NO'"
                    _, stdout, _ = client.exec_command(check_dr)
                    already_dist = stdout.read().decode().strip() == 'YES'

                    if not already_dist:
                        if log_callback:
                            log_callback("Updating Apache vhost DocumentRoot to dist/...")
                        sed_cmd = (
                            f"sed -i 's|DocumentRoot {path}|DocumentRoot {path}/dist|g' '{vhost_path}' && "
                            f"sed -i 's|<Directory {path}>|<Directory {path}/dist>|g' '{vhost_path}' && "
                            f"a2enmod mime rewrite 2>/dev/null; "
                            f"systemctl reload apache2 2>&1"
                        )
                        _, stdout, _ = client.exec_command(sed_cmd)
                        reload_out = stdout.read().decode().strip()
                        if log_callback:
                            log_callback("Apache vhost updated and reloaded.")
                            if reload_out:
                                log_callback(f"  {reload_out}")
                    else:

                        reload_cmd = "a2enmod mime rewrite 2>/dev/null; systemctl reload apache2 2>&1"
                        _, stdout, _ = client.exec_command(reload_cmd)
                        stdout.read()
                        if log_callback:
                            log_callback("Apache vhost already points to dist/")
                else:
                    if log_callback:
                        log_callback(f"No vhost config found at {vhost_path}")
                        log_callback("Built files are at document root — should work with default config.")
            else:
                if log_callback:
                    log_callback("Build ran but no dist/ folder (check build config)")

        return True, "Vite dependencies installed successfully"

    def install_wordpress(
        self,
        client,
        subdomain: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[bool, str]:
        """Install WordPress in the subdomain folder.
        If wp-config.php or wp-config-sample.php exists, just set permissions.
        Otherwise, download and extract fresh WordPress."""
        path = self.get_subdomain_path(subdomain)


        check_cmd = (
            f"test -f '{path}/wp-config.php' -o "
            f"-f '{path}/wp-config-sample.php' -o "
            f"-f '{path}/wp-login.php' && echo 'EXISTS' || echo 'NO'"
        )
        _, stdout, _ = client.exec_command(check_cmd)
        has_wp = stdout.read().decode().strip() == 'EXISTS'

        if has_wp:
            if log_callback:
                log_callback("WordPress files detected — skipping download.")
        else:
            if log_callback:
                log_callback("Downloading fresh WordPress...")
            cmd = (
                f"cd '{path}' && "
                f"wget -q https://wordpress.org/latest.tar.gz && "
                f"tar -xzf latest.tar.gz --strip-components=1 && "
                f"rm latest.tar.gz"
            )
            _, stdout, stderr = client.exec_command(cmd)
            stdout.read()
            error = stderr.read().decode().strip()
            if 'error' in error.lower() or 'failed' in error.lower():
                return False, f"WordPress download failed: {error}"
            if log_callback:
                log_callback("WordPress downloaded and extracted")


        if log_callback:
            log_callback("Setting WordPress permissions...")
        perm_cmd = (
            f"cd '{path}' && "
            f"find . -type d -exec chmod 755 {{}} \\; && "
            f"find . -type f -exec chmod 644 {{}} \\; && "
            f"chmod 600 wp-config.php 2>/dev/null; "
            f"chown -R www-data:www-data '{path}' 2>/dev/null || "
            f"chown -R apache:apache '{path}' 2>/dev/null"
        )
        _, stdout, _ = client.exec_command(perm_cmd)
        stdout.read()


        wp_dirs_cmd = (
            f"mkdir -p '{path}/wp-content/uploads' '{path}/wp-content/upgrade' && "
            f"chmod 775 '{path}/wp-content/uploads' '{path}/wp-content/upgrade'"
        )
        _, stdout, _ = client.exec_command(wp_dirs_cmd)
        stdout.read()

        if log_callback:
            log_callback("WordPress permissions set (dirs: 755, files: 644)")
            log_callback("Upload directories ready")


        check_comp = f"test -f '{path}/composer.json' && echo 'YES' || echo 'NO'"
        _, stdout, _ = client.exec_command(check_comp)
        if stdout.read().decode().strip() == 'YES':
            check_bin = "which composer 2>/dev/null"
            _, stdout, _ = client.exec_command(check_bin)
            if stdout.read().decode().strip():
                if log_callback:
                    log_callback("Running composer install...")
                comp_cmd = f"cd '{path}' && composer install --no-dev 2>&1"
                _, stdout, _ = client.exec_command(comp_cmd)
                comp_out = stdout.read().decode().strip()
                if log_callback and comp_out:
                    for line in comp_out.split('\n')[-5:]:
                        if line.strip():
                            log_callback(f"  {line.strip()}")

        return True, "WordPress setup complete"

    def clean_remote_directory(
        self,
        client,
        subdomain: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[bool, str]:
        """Remove all files and folders in the subdomain directory except .git.

        This ensures a clean slate before uploading new project files so that
        old artefacts (node_modules, dist, etc.) don't persist.
        """
        path = self.get_subdomain_path(subdomain)

        if log_callback:
            log_callback(f"Cleaning remote directory: {path}")
            log_callback("Removing old files (preserving .git)...")


        cmd = (
            f"cd '{path}' && "
            f"find . -mindepth 1 -maxdepth 1 -not -name '.git' -exec rm -rf {{}} +"
        )
        _, stdout, stderr = client.exec_command(cmd)
        stdout.read()
        err = stderr.read().decode().strip()

        if err and log_callback:
            log_callback(f"Clean warning: {err}")


        verify_cmd = f"find '{path}' -mindepth 1 -maxdepth 1 -not -name '.git' | wc -l"
        _, stdout, _ = client.exec_command(verify_cmd)
        remaining = stdout.read().decode().strip()

        if log_callback:
            log_callback(f"Clean complete — {remaining} item(s) remaining (excluding .git)")

        return True, f"Cleaned {path}"

    def upload_folder_to_server(
        self,
        client,
        local_folder: str,
        subdomain: str,
        log_callback: Optional[Callable[[str], None]] = None,
        clean_first: bool = False,
        snapshot_before_upload: bool = True,
    ) -> Tuple[bool, str]:
        """
        Upload a local folder's contents to the subdomain directory on the
        server via SFTP.  Preserves the folder structure.
        """
        import os

        remote_path = self.get_subdomain_path(subdomain)

        if snapshot_before_upload:
            snap_ok, snap_msg, snap_meta = self.create_deployment_snapshot(
                client,
                subdomain,
                operation="upload",
                reason="Auto snapshot before SFTP upload",
                log_callback=log_callback,
            )
            if log_callback:
                log_callback(f"[Snapshot] {snap_msg}")
                if snap_ok and snap_meta.get("snapshot_id"):
                    log_callback(f"[Snapshot] ID: {snap_meta['snapshot_id']}")
            if not snap_ok:
                return False, "Upload blocked: unable to create deployment snapshot."

        if log_callback:
            log_callback(f"Target server path: {remote_path}")
            log_callback(f"Source local path:  {local_folder}")


        if not os.path.isdir(local_folder):
            return False, f"Local folder does not exist: {local_folder}"


        if clean_first:
            self.clean_remote_directory(client, subdomain, log_callback)


        all_dirs = set()
        all_files = []

        for root, dirs, files in os.walk(local_folder):

            dirs[:] = [d for d in dirs if d != '.git' and d != 'node_modules']

            rel_root = os.path.relpath(root, local_folder)
            if rel_root == ".":
                target_dir = remote_path
            else:
                target_dir = f"{remote_path}/{rel_root.replace(os.sep, '/')}"

            all_dirs.add(target_dir)

            for fname in files:
                local_file = os.path.join(root, fname)
                remote_file = f"{target_dir}/{fname}"
                if rel_root == ".":
                    display = fname
                else:
                    display = f"{rel_root.replace(os.sep, '/')}/{fname}"
                all_files.append((local_file, remote_file, display))

        total_files = len(all_files)
        total_dirs = len(all_dirs)

        if log_callback:
            log_callback(f"Found {total_files} file(s) in {total_dirs} folder(s)")

        if total_files == 0:
            return False, f"No files found in {local_folder}"


        if log_callback:
            log_callback("Creating directories on server...")

        sorted_dirs = sorted(all_dirs)
        mkdir_parts = " ".join(f"'{d}'" for d in sorted_dirs)
        mkdir_cmd = f"mkdir -p {mkdir_parts}"
        _, _, stderr = client.exec_command(mkdir_cmd)
        mkdir_err = stderr.read().decode().strip()
        if mkdir_err and log_callback:
            log_callback(f"Warning creating dirs: {mkdir_err}")


        for d in sorted_dirs:
            check_cmd = f"[ -d '{d}' ] && echo 'ok' || echo 'MISSING'"
            _, stdout, _ = client.exec_command(check_cmd)
            result = stdout.read().decode().strip()
            if result != 'ok' and log_callback:
                log_callback(f"  WARNING: Directory not created: {d}")

        if log_callback:
            log_callback(f"Directories ready ({total_dirs} folders)")


        if log_callback:
            log_callback("Uploading files...")

        try:
            sftp = client.open_sftp()
        except Exception as e:
            return False, f"Failed to open SFTP session: {e}"

        uploaded_count = 0
        skipped = []

        try:
            for local_file, remote_file, display in all_files:
                try:
                    sftp.put(local_file, remote_file)
                    uploaded_count += 1
                    if log_callback:
                        log_callback(f"  [{uploaded_count}/{total_files}] {display}")
                except Exception as e:
                    skipped.append(f"{display}: {e}")
                    if log_callback:
                        log_callback(f"  FAILED: {display} -> {e}")
            sftp.close()
        except Exception as e:
            try:
                sftp.close()
            except Exception:
                pass
            return False, f"Upload failed: {e}"

        if log_callback:
            log_callback(f"\nUpload summary: {uploaded_count}/{total_files} file(s) to {remote_path}")
            if skipped:
                log_callback(f"Skipped {len(skipped)} file(s):")
                for s in skipped:
                    log_callback(f"  SKIP: {s}")

        if uploaded_count == 0 and total_files > 0:
            return False, f"Upload failed — 0 of {total_files} files uploaded"


        if log_callback:
            log_callback("Verifying files on server...")
        try:
            verify_cmd = f"find '{remote_path}' -type f -not -path '*/.git/*' | wc -l"
            _, v_out, _ = client.exec_command(verify_cmd)
            count_on_server = v_out.read().decode().strip()
            if log_callback:
                log_callback(f"Total files on server: {count_on_server}")
                if count_on_server == "0":
                    log_callback("WARNING: No files found on server after upload!")


            tree_cmd = f"find '{remote_path}' -not -path '*/.git/*' -type d | head -20"
            _, t_out, _ = client.exec_command(tree_cmd)
            tree = t_out.read().decode().strip()
            if tree and log_callback:
                log_callback("Server folders:")
                for line in tree.split('\n'):
                    log_callback(f"  {line}")
        except Exception:
            pass

        return True, f"Uploaded {uploaded_count} file(s) to {remote_path}"
