from datetime import datetime

from mmt_backend.db import get_db, init_db
from mmt_backend.db import get_db, User, Upload


def add_data():
    user1 = User(
        username="test",
        email="test@example.com",
        password="pbkdf2:sha256:50000$TCI4GzcX$0de171a4f4dac32e3364c7ddc7c14f3e2fa61f2d17574483f7ffbb431b4acb2f",
        is_admin=False,
        is_active=True,
    )

    user2 = User(
        username="other",
        email="other@example.com",
        password="pbkdf2:sha256:50000$kJPKsz6N$d2d4784f1b030a9761f5ccaeeaca413f27f2ecb76d6168407af962ddce849f79",
        is_admin=False,
        is_active=False,
    )

    user3 = User(
        username="admin",
        email="admin@example.com",
        password="pbkdf2:sha256:50000$TCI4GzcX$0de171a4f4dac32e3364c7ddc7c14f3e2fa61f2d17574483f7ffbb431b4acb2f",
        is_admin=True,
        is_active=True,
    )

    upload1 = Upload(
        filename="testfile.mp4",
        size=5_000_000,
        content_type="video/mp4",
        user_id=1,
        created_at=datetime(2024, 1, 1),
    )

    db = get_db()

    db.session.add_all([user1, user2, user3])
    db.session.add_all([upload1])

    db.session.commit()
