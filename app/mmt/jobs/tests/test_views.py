from http import HTTPStatus

import pytest
from django.urls import reverse

URL = '/jobs/'


@pytest.mark.django_db
def test_an_anonymous_request_is_redirected_to_login(client):
    response = client.get(URL)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url.startswith(reverse('account_login'))


def test_a_user_without_the_permission_is_forbidden(client, bob):
    client.force_login(bob)

    response = client.get(URL)

    assert response.status_code == HTTPStatus.FORBIDDEN


def test_a_transcriber_sees_only_their_own_jobs(
    client, alice, bob, make_transcription_job, make_extraction_job
):
    make_transcription_job(alice, 'alice_interview.mp4')
    make_extraction_job(alice, 'Alice transcript')
    make_transcription_job(bob, 'bob_interview.mp4')
    make_extraction_job(bob, 'Bob transcript')
    client.force_login(alice)

    response = client.get(URL)
    content = response.content.decode()

    assert response.status_code == HTTPStatus.OK
    assert 'alice_interview.mp4' in content
    assert 'Alice transcript' in content
    assert 'bob_interview.mp4' not in content
    assert 'Bob transcript' not in content
