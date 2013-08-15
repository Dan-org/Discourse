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
        if (xhr.status == 0) {
            addError("Error communicating with the server.");
        } else {
            addError("Error posting message: " + xhr.statusText);
        }
        form.find('input').attr('disabled', null);
        form.find('textarea').attr('disabled', null).focus();
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

        if (!comment.parent) {
            newComment.addClass('repliable');
        }

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

    form.submit(submit);
    return form;
}

function resetForm(form) {
    form.find('textarea').attr('disabled', null);
    form.find('input').attr('disabled', null);
    form[0].reset();
}

function createReplyForm(options) {
    var comment = options.comment;
    var form = comment.closest('.repliable').find('form');

    if (form.length == 0) {
        var prototype = comment.closest('.thread').find('form').eq(0);
        form = prototype.clone().hide().appendTo(comment).addClass('active').fadeIn();
        commentForm(form[0]);
        resetForm(form);
    } else {
        form.hide().fadeIn();
        resetForm(form);
    }

    if (options.edit) {
        form.find("input[name=pk]").val(options.edit);
    } else {
        form.find("input[name=pk]").val(null);
    }

    if (options.reply) {
        form.addClass('reply');
        form.find("input[name=parent]").val(options.reply);
    } else {
        form.find("input[name=parent]").val(null);
    }

    form.find('textarea').val(options.text || "");
    form.find('textarea').focus();

    form.find('textarea').one('blur', function() {
        var body = form.find('textarea').val().trim();
        if (body.length == 0) form.hide();
    })
    
    return form;
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
    var comment = link.closest('.comment');

    var form = createReplyForm({
        comment: comment,
        edit: comment.attr("rel"),
        text: comment.find('.raw').html()
    });

    return false;
}

function replyAction(e) {
    var link = $(e.target);
    var comment = link.closest('.repliable');

    var form = createReplyForm({
        comment: comment,
        reply: comment.attr("rel")
    });

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

function deleteComment(source) {
    var meta = source.find('.meta').eq(0);
    var info = source.find('.info').eq(0);

    source.addClass('deleted');
    meta.find('.profile-pic')
            .attr('href', '#')
            .find('img')
                .attr('src', "/static/img/star.jpg")
                .attr('alt', 'deleted')
                .attr('title', 'deleted');

    info.find('.name').replaceWith('<span class="name">deleted</span>');

    if (source.find('.comment').length == 0) {
        source.fadeOut();
    } else {
        info.fadeTo('fast', .2).fadeTo('normal', .8);
    }
}

function updateComment(source, comment) {
    var meta = source.find('.meta').eq(0);
    var info = source.find('.info').eq(0);
    meta.find('.score').empty().append(comment.value);

    info.find('.content').empty().append(comment.body);
    info.find('.raw').empty().append(comment.raw);

    if (comment.deleted) {
        deleteComment(source);
    }
}

function addNewComment(comment) {
    var thread = $('.thread').filter(function() {
        return $(this).attr('rel') == comment.path;
    });
    if (thread.length == 0) return;

    var existing = thread.find('.comment').filter(function() {
        return $(this).attr('rel') == comment.id;
    });

    if (existing.length > 0) {
        console.log("Updating comment...");
        return updateComment(existing, comment);
    }

    var form = thread.find('form').eq(0);
    var newComment = $('<div class="comment new">')
                        .attr("id", "comment-" + comment.id)
                        .attr("rel", comment.id)
                        .append(comment['_html']);

    if (form.hasClass("response-form"))
        form.before(newComment);
    else
        form.after(newComment);

    if (!comment.parent) {
        newComment.addClass('repliable');
    }

    window.scrollTo(window.scrollX, window.scrollY + newComment.height());
    newComment.hide().fadeIn();

    if (form.hasClass('reply')) {
        form.remove()
    } else {
        form[0].reset();
    }
}


$(function() {
    $('.discourse .thread').each(function(i, e) {
        socket.emit("follow", $(e).attr('rel'));
    })
    
    $('.discourse .thread form').each(function(i, e) { commentForm(e) });

    $(document).on('click', '.discourse .thread .comment .actions .delete', deleteAction);
    $(document).on('click', '.discourse .thread .comment .actions .edit', editAction);
    $(document).on('click', '.discourse .thread .comment .actions .reply', replyAction);
    $(document).on('click', '.discourse .thread .comment .upvote', voteAction(1));
    $(document).on('click', '.discourse .thread .comment .downvote', voteAction(-1));
});


if (window.io == undefined) {
    var socket = {
        emit: $.noop
    };
} else {
    var socket = io.connect("/discourse");

    socket.on('connect', function () {
        console.log("Connected!");
    });

    socket.on('comment', function (comment) {
        addNewComment(comment);
    });

    socket.on('vote', function (data) {
        var id = data.id;
        var value = data.value;
        $('.comment').each(function(i, e) {
            var source = $(e);
            if (source.attr('rel') == id) {
                var current = source.find('.score')[0].innerHTML;
                if (value + "" == current) return;
                source.find('.score').eq(0).empty().append(value).fadeOut().fadeIn();
            }
        });
    });

    socket.on('delete', function(id) {
        $('.comment').each(function(i, e) {
            var source = $(e);
            if (source.attr('rel') == id) {
                deleteComment(source);
            }
        });
    });
}