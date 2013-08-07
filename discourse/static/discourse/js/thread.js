function commentForm(e) {
    var form = $(e);
    // Todo: length counter | ajax indicator | hide comments | reply | edit | report

    function addError(err) {
        var errors = form.find('ul.errors');
        if (errors.length == 0) {
            errors = $('<ul class="errors">').prependTo(form);
        }
        errors.append($("<li>").append(err));
    }

    function clearErrors() {
        form.find('ul.errors').remove();
    }

    function onSuccess(response) {
        addComment(response['_html'])
    }

    function onFailure(xhr, status, error) {
        console.log("onFailure", xhr, status, error);
    }

    function addComment(html) {
        var newComment = $('<div class="new-comment">').append(html);
        form.before(newComment);
        window.scrollTo(window.scrollX, window.scrollY + newComment.height());
        newComment.hide().fadeIn();
        if (form.hasClass('reply')) {
            form.remove()
        } else {
            form[0].reset();
        }
    }

    function validate() {
        clearErrors();
        var bodyField = form.find('textarea[name=body]');
        var body = bodyField.val().trim();

        if (body.length == 0) {
            console.log("body.length", bodyField, bodyField.val());
            addError("Please type a message.");
            bodyField.focus();
            return false;
        }

        return true;
    }

    function submit() {
        if (!validate()) {
            return false;
        }

        $.ajax({
            type: form.attr('method'),
            url: form.attr('action'),
            data: form.serialize(),
            success: onSuccess,
            error: onFailure
        });

        return false;
    }

    form.submit(submit);
    return form;
}

/// Delete Action ///
function deleteAction(e) {
    var link = $(e.target);
    var comment = link.closest('.comment');

    $.ajax({
        url: link.attr('href'),
        success: function() {
            comment.fadeOut('normal', function() {
                comment.remove();
            });
        },
        error: function() {
            comment.fadeOut('fast').fadeIn('fast');
        }
    });

    e.preventDefault();
    return false;
}


function replyAction(e) {
    var link = $(e.target);
    var comment = link.closest('.comment');
    var form = link.closest('.discourse').find('form.add-comment').first()
                   .clone()
                   .addClass('reply');
    var cancel = $('<input type="button" value="Cancel" class="cancel"/>')
                   .prependTo(form.find('.buttons'))
                   .click(function() {
                        form.remove();
                   });

    comment.after(form);

    form.find('textarea').attr('placeholder', "add your reply here").focus();
    form.find('input[name=parent]').val( comment.attr('rel') );
    form.find('input[type=submit]').val( "Add Reply" );

    commentForm(form);

    e.preventDefault();
    return false;
}


function voteAction(updown) {
    return function(e) {
        var arrow = $(e.target);
        var comment = arrow.closest('.comment');
        var thread = comment.closest('.thread');
        var form = thread.find('form');
        var dir = updown;

        if (arrow.hasClass('selected')) {
            comment.find('.voting a').removeClass('selected');
            dir = 0;
        } else {
            comment.find('.voting a').removeClass('selected');
            arrow.addClass('selected');
        }

        $.ajax({
            type: 'post',
            url: '/discourse/vote/',
            data: {dir: dir, pk: comment.attr('rel')},
            success : function(value) {
                comment.find('.score').empty().append(value);
            }
        })
    }
}


$(function() {
    $('.discourse .thread form').each(function(i, e) { commentForm(e) });

    $(document).on('click', '.discourse .thread .comment .actions .delete', deleteAction);
    $(document).on('click', '.discourse .thread .comment .actions .reply', replyAction);
    $(document).on('click', '.discourse .thread .comment .upvote', voteAction(1));
    $(document).on('click', '.discourse .thread .comment .downvote', voteAction(-1));
})



