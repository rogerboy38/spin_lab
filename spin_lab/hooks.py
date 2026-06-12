app_name = "spin_lab"
app_title = "Spin Lab"
app_publisher = "rogerboy38"
app_description = (
    "Educational slot machine simulator & next-token probability research lab. "
    "Pure RNG, virtual credits only - no real-money gambling."
)
app_email = "rogerboy38@users.noreply.github.com"
app_license = "MIT"

# Seed default themes on install
after_install = "spin_lab.install.after_install"

# Re-seed (idempotent) so new built-in themes appear after updates
after_migrate = ["spin_lab.install.after_migrate"]

# Scheduled cleanup of old simulation spins (keeps DB small)
scheduler_events = {
    "daily": [
        "spin_lab.engine.maintenance.prune_old_spins",
    ],
}

# Website route for the canvas lab page
website_route_rules = [
    {"from_route": "/spin-lab", "to_route": "spin_lab"},
]
