-- input_apps definition

CREATE TABLE input_apps (
            app_id TEXT NOT NULL PRIMARY KEY,
            downloaded BOOLEAN DEFAULT 0,
            metadata BOOLEAN DEFAULT 0, -- this indicates if the metadata of the app has been downloaded
            device TEXT DEFAULT NULL -- this is the device that the app is currently downloaded on
        );

CREATE INDEX idx2_app_id ON input_apps (app_id);

-- error_apps definition

CREATE TABLE error_apps (
            app_id TEXT NOT NULL,
            device TEXT NOT NULL,
            error TEXT NOT NULL,
            PRIMARY KEY (app_id, device, error),
            FOREIGN KEY (app_id) REFERENCES input_apps (app_id) ON DELETE CASCADE
        );

CREATE INDEX idx_error ON error_apps (error);
CREATE INDEX idx_app_id ON error_apps (app_id);