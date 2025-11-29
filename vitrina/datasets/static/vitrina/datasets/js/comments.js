document.addEventListener("DOMContentLoaded", function() {
    const getCsrfToken = () => document.querySelector('[name=csrfmiddlewaretoken]').value;

    const apiCall = (url, successCallback, errorMessage) => {
        fetch(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                successCallback(data);
            } else {
                alert(errorMessage);
            }
        })
        .catch(error => {
            console.error(error);
            alert('Klaida');
        });
    };

    window.openDeleteModal = (commentId) => {
        document.getElementById(`delete-modal-${commentId}`).classList.add('is-active');
    };

    window.closeDeleteModal = (commentId) => {
        document.getElementById(`delete-modal-${commentId}`).classList.remove('is-active');
    };

    document.querySelectorAll('.show-delete-form').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            openDeleteModal(button.id.replace('delete-', ''));
        });
    });

    document.querySelectorAll('.delete-confirm').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const commentId = button.dataset.commentId;
            apiCall(
                `/comments/${commentId}/delete/`,
                () => {
                    closeDeleteModal(commentId);
                    location.reload();
                },
                'Nepavyko ištrinti komentaro'
            );
        });
    });

    document.querySelectorAll('.edit-button').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const commentId = button.dataset.commentId;
            document.getElementById(`comment-display-${commentId}`).classList.add('is-hidden');
            document.getElementById(`comment-edit-${commentId}`).classList.remove('is-hidden');
        });
    });

    document.querySelectorAll('.cancel-edit').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const commentId = button.dataset.commentId;
            document.getElementById(`comment-edit-${commentId}`).classList.add('is-hidden');
            document.getElementById(`comment-display-${commentId}`).classList.remove('is-hidden');
        });
    });

    document.querySelectorAll('.edit-form').forEach(form => {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const commentId = form.dataset.commentId;
            fetch(`/comments/${commentId}/edit/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrfToken() },
                body: new FormData(form)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert(data.error || 'Nepavyko redaguoti komentaro');
                }
            })
            .catch(error => {
                console.error(error);
                alert('Klaida');
            });
        });
    });

    document.querySelectorAll('.reply-toggle-button').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const replyForm = button.closest('article').nextElementSibling;
            if (replyForm && replyForm.id.startsWith('media-')) {
                replyForm.classList.toggle('is-hidden');
            }
        });
    });
});