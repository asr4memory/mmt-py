INSERT INTO user (username, email, password, admin, activated)
VALUES
    (
        'test',
        'test@example.com',
        'pbkdf2:sha256:50000$TCI4GzcX$0de171a4f4dac32e3364c7ddc7c14f3e2fa61f2d17574483f7ffbb431b4acb2f',
        false,
        true
    ),
    (
        'other',
        'other@example.com',
        'pbkdf2:sha256:50000$kJPKsz6N$d2d4784f1b030a9761f5ccaeeaca413f27f2ecb76d6168407af962ddce849f79',
        false,
        false
    ),
    (
        'admin',
        'admin@example.com',
        'pbkdf2:sha256:50000$TCI4GzcX$0de171a4f4dac32e3364c7ddc7c14f3e2fa61f2d17574483f7ffbb431b4acb2f',
        true,
        true
    );

INSERT INTO upload (filename, size, content_type, user_id, created)
VALUES
    ('testfile.mp4', 5000000, "video/mp4", 1, '2024-01-01 00:00:00');
