#!/bin/sh
# Installs the test-harness shell wrapper and stub commands inside the image.
set -e
# /bin/sh wrapper: logs every "sh -c <cmd>" issued by the program under test
# (only the process that has XINDI_SHELL_LOG in its environment).
ln -sf /bin/dash /bin/dash.real 2>/dev/null || true
cat > /bin/sh.xindi <<'EOS'
#!/bin/dash
if [ "$1" = "-c" ] && [ -n "$XINDI_SHELL_LOG" ]; then
    printf '%s\036' "$2" >> "$XINDI_SHELL_LOG"
fi
unset XINDI_SHELL_LOG
exec /bin/dash "$@"
EOS
chmod +x /bin/sh.xindi
ln -sf /bin/sh.xindi /bin/sh
for f in /opt/support/stubs/*; do
    install -m 755 "$f" /usr/local/sbin/
done
install -m 755 /opt/support/stubs/systemctl /usr/bin/systemctl
mkdir -p /opt/support/state
