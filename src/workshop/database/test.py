import os

# Print the current working directory
print(f"Current working directory: {os.getcwd()}")

# Check if the database file exists
db_path = "/workspaces/build-your-first-agent-with-azure-ai-agent-service-workshop/src/workshop/database/contoso-sales.db"
if os.path.exists(db_path):
    print(f"Database found at: {db_path}")
else:
    print(f"Database not found at: {db_path}")
