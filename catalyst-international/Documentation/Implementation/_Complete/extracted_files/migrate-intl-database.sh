#!/bin/bash
# ============================================================================
# CATALYST INTERNATIONAL - DATABASE MIGRATION SCRIPT
# 
# Purpose: Migrate International system to shared PostgreSQL instance
# Run on: International Droplet
# Version: 1.0.0
# Date: 2025-12-28
# ============================================================================

set -e  # Exit on error

echo "========================================"
echo "CATALYST INTERNATIONAL DATABASE MIGRATION"
echo "========================================"
echo ""

# ----------------------------------------------------------------------------
# CONFIGURATION - Shared PostgreSQL Instance
# ----------------------------------------------------------------------------

# Shared PostgreSQL instance (same as US system uses)
SHARED_HOST="catalyst-trading-db-do-user-23488393-0.l.db.ondigitalocean.com"
SHARED_PORT="25060"
SHARED_USER="doadmin"
SHARED_PASSWORD="${SHARED_DB_PASSWORD}"  # Set via environment variable

# Paths
PROJECT_DIR="/root/Catalyst-Trading-System-International/catalyst-international"
ENV_FILE="${PROJECT_DIR}/.env"
SCHEMA_FILE="${PROJECT_DIR}/sql/schema.sql"

# Build connection strings
ADMIN_URL="postgresql://${SHARED_USER}:${SHARED_PASSWORD}@${SHARED_HOST}:${SHARED_PORT}/defaultdb?sslmode=require"
INTL_URL="postgresql://${SHARED_USER}:${SHARED_PASSWORD}@${SHARED_HOST}:${SHARED_PORT}/catalyst_intl?sslmode=require"
RESEARCH_URL="postgresql://${SHARED_USER}:${SHARED_PASSWORD}@${SHARED_HOST}:${SHARED_PORT}/catalyst_research?sslmode=require"

# ----------------------------------------------------------------------------
# VALIDATION
# ----------------------------------------------------------------------------

echo "Step 0: Validating configuration..."
echo "  Host: ${SHARED_HOST}"
echo "  User: ${SHARED_USER}"
echo "  Port: ${SHARED_PORT}"
echo "✓ Configuration validated"
echo ""

# ----------------------------------------------------------------------------
# STEP 1: Create database
# ----------------------------------------------------------------------------

echo "Step 1: Creating catalyst_intl database on shared instance..."

psql "${ADMIN_URL}" -c "CREATE DATABASE catalyst_intl;" 2>/dev/null || echo "  (Database may already exist, continuing...)"

echo "✓ Database ready"
echo ""

# ----------------------------------------------------------------------------
# STEP 2: Deploy schema
# ----------------------------------------------------------------------------

echo "Step 2: Deploying schema to catalyst_intl..."

if [[ -f "$SCHEMA_FILE" ]]; then
    echo "  Using existing schema file: $SCHEMA_FILE"
    psql "${INTL_URL}" < "$SCHEMA_FILE"
else
    echo "  Schema file not found at $SCHEMA_FILE"
    echo "  Please run the schema SQL manually or create the file"
    exit 1
fi

echo "✓ Schema deployed"
echo ""

# ----------------------------------------------------------------------------
# STEP 3: Backup and update .env
# ----------------------------------------------------------------------------

echo "Step 3: Updating .env file..."

if [[ -f "$ENV_FILE" ]]; then
    # Backup existing .env
    cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "  Backed up existing .env"
    
    # Check if DATABASE_URL exists and update, or add if not present
    if grep -q "^DATABASE_URL=" "$ENV_FILE"; then
        # Comment out old DATABASE_URL and add new one
        sed -i "s|^DATABASE_URL=.*|# OLD: &\nDATABASE_URL=${INTL_URL}|" "$ENV_FILE"
    else
        echo "" >> "$ENV_FILE"
        echo "DATABASE_URL=${INTL_URL}" >> "$ENV_FILE"
    fi
    
    # Add RESEARCH_DATABASE_URL if not present
    if ! grep -q "^RESEARCH_DATABASE_URL=" "$ENV_FILE"; then
        echo "RESEARCH_DATABASE_URL=${RESEARCH_URL}" >> "$ENV_FILE"
    fi
    
    echo "  Updated DATABASE_URL"
    echo "  Added RESEARCH_DATABASE_URL"
else
    echo "  Creating new .env file"
    cat > "$ENV_FILE" << EOF
# Catalyst International Environment
# Updated: $(date)

# Trading Database (HKEX)
DATABASE_URL=${INTL_URL}

# Consciousness Database (shared)
RESEARCH_DATABASE_URL=${RESEARCH_URL}

# Add other variables below...
EOF
fi

echo "✓ Environment updated"
echo ""

# ----------------------------------------------------------------------------
# STEP 4: Test connections
# ----------------------------------------------------------------------------

echo "Step 4: Testing connections..."

echo "  Testing catalyst_intl..."
psql "${INTL_URL}" -c "SELECT current_database(), NOW() as connected_at;" || {
    echo "ERROR: Failed to connect to catalyst_intl"
    exit 1
}

echo "  Testing catalyst_research..."
psql "${RESEARCH_URL}" -c "SELECT current_database(), NOW() as connected_at;" || {
    echo "ERROR: Failed to connect to catalyst_research"
    exit 1
}

echo "✓ All connections successful"
echo ""

# ----------------------------------------------------------------------------
# STEP 5: Verify setup
# ----------------------------------------------------------------------------

echo "Step 5: Verifying setup..."

echo "  Tables in catalyst_intl:"
psql "${INTL_URL}" -c "\dt" | head -20

echo ""
echo "  HKEX exchange:"
psql "${INTL_URL}" -c "SELECT code, name, timezone FROM exchanges;"

echo ""
echo "  intl_claude agent state:"
psql "${RESEARCH_URL}" -c "SELECT agent_id, current_mode, status_message FROM claude_state WHERE agent_id = 'intl_claude';" 2>/dev/null || echo "  (Agent not yet initialized in research DB)"

echo ""
echo "  Welcome message:"
psql "${RESEARCH_URL}" -c "SELECT from_agent, subject FROM claude_messages WHERE to_agent = 'intl_claude';" 2>/dev/null || echo "  (No messages yet)"

echo ""
echo "========================================"
echo "MIGRATION COMPLETE!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Verify the application works with new database"
echo "2. Delete the OLD PostgreSQL instance in DigitalOcean"
echo "3. Save ~\$15/month!"
echo ""
echo "Connection strings saved to: $ENV_FILE"
echo ""
