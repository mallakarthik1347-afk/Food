import os
from foodMenuWebsite import app, db
from foodMenuWebsite.seed_data import migrate_and_seed

# Ensure database tables and initial seed data exist
with app.app_context():
    db.create_all()
    # Check if restaurant table has rows, if not run migration and seed
    try:
        from foodMenuWebsite.models import Restaurant
        if Restaurant.query.count() == 0:
            print("Seeding initial restaurant data...")
            migrate_and_seed()
    except Exception as e:
        print(f"Database check/migration note: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() in ['true', '1']
    app.run(host='0.0.0.0', port=port, debug=debug)
