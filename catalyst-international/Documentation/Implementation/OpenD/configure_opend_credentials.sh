#!/bin/bash
# OpenD Credential Configuration Script

OPEND_DIR="/home/craig/Downloads/OpenD"
CONFIG_FILE="$OPEND_DIR/OpenD.xml"

echo "🔧 OpenD Credential Configuration"
echo "=================================="

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ OpenD.xml not found at $CONFIG_FILE"
    exit 1
fi

echo "📝 Current configuration template uses placeholders for security."
echo "   You need to replace the following in OpenD.xml:"
echo ""
echo "1. Replace 'YOUR_MOOMOO_ACCOUNT' with your actual MooMoo account"
echo "   - This can be your User ID, phone number (+86 format), or email"
echo ""
echo "2. Replace 'YOUR_MOOMOO_PASSWORD' with your actual password"
echo "   - Or use MD5 hash by uncommenting login_pwd_md5 line"
echo ""

read -p "Do you want to configure credentials now? (y/n): " configure_now

if [ "$configure_now" = "y" ] || [ "$configure_now" = "Y" ]; then
    echo ""
    read -p "Enter your MooMoo account (User ID/Phone/Email): " moomoo_account
    read -s -p "Enter your MooMoo password: " moomoo_password
    echo ""

    # Escape special characters for sed
    escaped_account=$(printf '%s\n' "$moomoo_account" | sed 's/[[\.*^$()+?{|]/\\&/g')
    escaped_password=$(printf '%s\n' "$moomoo_password" | sed 's/[[\.*^$()+?{|]/\\&/g')

    # Replace placeholders with actual credentials
    sed -i "s/YOUR_MOOMOO_ACCOUNT/$escaped_account/g" "$CONFIG_FILE"
    sed -i "s/YOUR_MOOMOO_PASSWORD/$escaped_password/g" "$CONFIG_FILE"

    echo "✅ Credentials configured successfully!"
    echo ""
    echo "⚠️  SECURITY NOTE:"
    echo "   - Your password is stored in plain text in OpenD.xml"
    echo "   - Consider using MD5 hash instead for better security"
    echo "   - Protect OpenD.xml file permissions:"
    echo "     chmod 600 $CONFIG_FILE"

    chmod 600 "$CONFIG_FILE"
    echo "   ✅ File permissions set to 600 (owner read/write only)"
else
    echo ""
    echo "⚠️  Manual configuration required:"
    echo "   Edit: $CONFIG_FILE"
    echo "   Replace: YOUR_MOOMOO_ACCOUNT and YOUR_MOOMOO_PASSWORD"
fi

echo ""
echo "🔐 To use MD5 password hash instead:"
echo "   1. Generate MD5 hash: echo -n 'your_password' | md5sum"
echo "   2. Comment out <login_pwd> line in OpenD.xml"
echo "   3. Uncomment and update <login_pwd_md5> with the hash"
echo ""
echo "📂 Log directory will be created at: /var/log/opend"
echo "   sudo mkdir -p /var/log/opend"
echo "   sudo chown $USER:$USER /var/log/opend"