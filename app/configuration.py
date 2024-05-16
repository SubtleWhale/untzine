from pathlib import Path
import sys, os, json

def load_configuration(app_name : str) -> dict:

    app_name = app_name.lower()

    # Read JSON configuration file if provided
    if len(sys.argv) > 1 and Path(sys.argv[1]).exists():
        configuration = json.load(open(sys.argv[1]))
    else:
        configuration = dict()

    # Parse environnement variables and add them to config
    for key, value in dict(os.environ).items():

        key_path = list(map(lambda x: x.lower(), key.split('__')))

        # Barbant Music Downloader configuration value
        if key_path[0] == app_name:

            update = configuration
            
            for k in key_path[1:-1]:

                if k in update and type(update[k]) is dict:
                    update = configuration[k]
                else:
                    update[k] = dict()
                    update = update[k]
            
            # Add new value or erase JSON configured value
            update[key_path[-1]] = value
    
    return configuration