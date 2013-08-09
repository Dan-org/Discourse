function commentForm(e) {
    var form = $(e);
    var textarea = form.find('textarea');
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
        var existing = $("#comment-" + response.id);
        if (existing.length > 0) {
            children = existing.find('.comment').detach();
            existing.empty().append(response['_html']).append(children);
            existing.hide().fadeIn();
        } else {
            addComment(response);
        }

        resetForm(form);

        if (form.hasClass("response-form")) {
            form.removeClass('active').hide();
        }
    }

    function onFailure(xhr, status, error) {
        console.log("onFailure", xhr, status, error);
    }

    function addComment(comment) {
        var newComment = $('<div class="comment new">')
                            .attr("id", "comment-" + comment.id)
                            .attr("rel", comment.id)
                            .append(comment['_html']);
        if (form.hasClass("response-form"))
            form.before(newComment);
        else
            form.after(newComment);

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
        var body = textarea.val().trim();

        if (body.length == 0) {
            console.log("body.length", textarea, textarea.val());
            addError("Please type a message.");
            textarea.focus();
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

        textarea.attr('disabled', 'disabled');
        form.find('input').attr('disabled', 'disabled');

        return false;
    }

    function blur() {
        var body = textarea.val().trim();
        if (body.length == 0) form.hide().removeClass('active');
    }

    if (form.find('input[name=parent]').val().length > 0)
        textarea.blur(blur);

    form.submit(submit);
    return form;
}

function resetForm(form) {
    form.find('textarea').attr('disabled', null);
    form.find('input[name=pk]').val("");
    form.find('input').attr('disabled', null);
    form[0].reset();
}

/// Actions ///
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

function editAction(e) {
    var link = $(e.target);
    var repliable = link.closest('.repliable');
    var comment = link.closest('.comment');
    var pk = comment.attr("rel");
    var text = comment.find('.raw').html();
    var form = repliable.find('form');

    resetForm(form);

    form.find("input[name=pk]").val(pk);
    form.find('textarea').val(text);

    if (form.hasClass('active')) {
        form.css('opacity', 0).animate({opacity: 1});
        form.find('textarea').focus();
        return false;
    }

    form.hide().addClass('active').fadeIn();
    form.find('textarea').focus();
    return false;
}

function replyAction(e) {
    var link = $(e.target);
    var repliable = link.closest('.repliable');
    var form = repliable.find('form');
    console.log(repliable);

    resetForm(form);

    if (form.hasClass('active')) {
        form.css('opacity', 0).animate({opacity: 1});
        form.find('textarea').focus();
        return false;
    }

    form.hide().addClass('active').fadeIn();
    form.find('textarea').focus();
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
    $(document).on('click', '.discourse .thread .comment .actions .edit', editAction);
    $(document).on('click', '.discourse .thread .comment .actions .reply', replyAction);
    $(document).on('click', '.discourse .thread .comment .upvote', voteAction(1));
    $(document).on('click', '.discourse .thread .comment .downvote', voteAction(-1));
})



