jQuery(document).ready(function($){
    "use strict";

    /* CSRF protection. The csrf_token variable should be set in the
     * '<controller>/base.html' template.
     */
    $(document).ajaxSend(function(e, xhr, s) {
        if (s.type == 'POST' || s.type == 'PUT') {
            xhr.setRequestHeader('X-CSRF-Token', csrf_token);
        }
    });

    $('.remove-confirm').on('click',function(e){
        e.preventDefault();
        var form = $(this).parents('form');
        var info = form[0][1].value;
        swal({
            title: "Just double checking",
            text: "Are you sure you want to remove " + info + " from the group?",
            showCancelButton: true,
            confirmButtonText: "Yes, I'm sure!",
            closeOnConfirm: true
        }, function(isConfirm){
            if (isConfirm) form.submit();
        });
    })

    /* Comments
     *
     * Comments are rendered server-side, but the comment editor is client-side.
     * The editor is placed just before the comment it's editing, or last if
     * the editor is for a new comment.
     */
    var editorTemplate = $('#editor-template').html();
    var markdown = window.markdownit();

    /* Render Markdown content as HTML in the comment editor. */
    function render(editor) {
        var content = editor.find('textarea').val();
        var html = content ? markdown.render(content) : '<p>Nothing to preview</p>';
        editor.find('.markdown-body').empty().append(html);
    }

    /* Remove a comment or editor and, if necessary, its container. */
    function removeComment(comment) {
        var container = comment.parents('.comment-container');
        comment.remove();
        if (container.children().length == 0) {
            container.parent('tr').remove();
        }
    }

    $('body').on('click', '.comment-add', function (e) {
        e.preventDefault();
        // try to find a comment container in the next row
        var row = $(this).parents('tr');
        var container = row.next().find('.comment-container');
        if (container.length == 0) {
            // create a comment container
            var containerRow = $('<tr></tr>');
            containerRow.data('line', row.data('line'));
            row.after(containerRow);
            container = $('<td class="comment-container" colspan=3></td>');
            containerRow.append(container);
        }
        // Don't add more than one new comment editor
        var editor = container.children().last().filter('.comment-editor');
        if (editor.length == 0) {
            container.append(editorTemplate);
        }
        render(container.find('.comment-editor'));
    });

    $('body').on('click', '.comment-edit', function (e) {
        e.preventDefault();
        var comment = $(this).parents('.comment');
        var editor = $(editorTemplate);
        editor.find('textarea').val(comment.data('message'));
        comment.before(editor);
        comment.hide();
        render(editor);
    });

    $('body').on('click', '.comment-delete', function (e) {
        e.preventDefault();
        var comment = $(this).parents('.comment');
        swal({
            title: "Just double checking",
            text: "Are you sure you want to delete this comment?",
            showCancelButton: true,
            confirmButtonText: "Yes, I'm sure!",
            closeOnConfirm: true,
        }, function() {
            $.ajax({
                url: '/comments/' + comment.data('id'),
                type: 'DELETE'
            }).done(function () {
                comment.fadeOut(function () { removeComment(comment) });
            }).fail(function () {
                swal('Oops, something went wrong. Try again?', 'error');
            });
        });
    });

    $('body').on('change keyup paste cut', '.comment-write', 
            debounce(function(e) {
        var editor = $(this).parents('.comment-editor');
        render(editor);
    }, 250));

    $('body').on('click', '.comment-cancel', function(e) {
        e.preventDefault();
        var editor = $(this).parents('.comment-editor');
        editor.next().show();  // show edited comment
        removeComment(editor);
    });

    $('body').on('click', '.comment-save', function (e) {
        e.preventDefault();
        var editor = $(this).parents('.comment-editor');
        var message = editor.find('textarea').val();
        var comment = editor.next();

        // Disable editor during AJAX request
        editor.addClass('comment-editor-disabled');

        var request;
        if (comment.length > 0) {
            request = {
                url: '/comments/' + comment.data('id'),
                method: 'PUT',
                data: {
                    message: message
                }
            };
        } else {  // new comment
            var sourceFile = editor.parents('.source-file');
            request = {
                url: '/comments/',
                method: 'POST',
                data: {
                    backup_id: sourceFile.data('backupId'),
                    filename: sourceFile.data('filename'),
                    line: editor.parents('tr').data('line'),
                    message: message
                }
            };
        }
        $.ajax(request).done(function(newComment) {
            editor.before(newComment);
            editor.remove();
            comment.remove();
        }).fail(function () {
            editor.removeClass('comment-editor-disabled');
            swal('Oops, something went wrong. Try again?', 'error');
        })
    });

});
