DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS upload;

CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT NOT NULL,
    locale TEXT NOT NULL DEFAULT "en",
    password TEXT NOT NULL,
    admin BOOLEAN NOT NULL DEFAULT false,
    activated BOOLEAN NOT NULL DEFAULT false,
    can_upload BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE upload (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    filename TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT "created",
    size INTEGER NOT NULL DEFAULT 0,
    transferred INTEGER NOT NULL DEFAULT 0,
    content_type TEXT NOT NULL,
    checksum_server TEXT NOT NULL DEFAULT "",
    checksum_client TEXT NOT NULL DEFAULT "",
    FOREIGN KEY (user_id) REFERENCES user (id)
)
