// When the page loads, have discourse follow all threads
$(function() {
    following = {};

    $('.discourse.stream').each(function(i, e) {
        var channel = $(e).attr('data-channel-id');
        if (following[channel]) return;
        following[channel] = true;
        discourse.follow(channel);
    })
});

// When a user focuses on a textarea it adds "focused" to the form this allows us to do things like 
// change the color of the submit button to blue.
$(document).on('focus', '.discourse .thread textarea', function(e) {
    $(this).closest('form').addClass('focused');
    $(this).closest('form').addClass('editing');
});

$(document).on('blur', '.discourse .thread textarea', function(e) {
    var form = $(this).closest('form');
    setTimeout(function() {
        form.removeClass('focused');
        if (form.find('textarea').val() == '')
            form.removeClass('editing');
    }, 100);
});

// When 'delete' is pressed on a message, it is deleted.
$(document).on('click', '.discourse .messages .act-delete', deleteMessage);

// When 'reply' is pressed on a comment, the form is copied and added to the end of the subthread.
$(document).on('click', '.discourse .thread .controls .reply', function(e) {
    replyTo($(e.target).closest('.comment'));
    e.preventDefault();
});

// When the user blurs on a reply form, clear them.
$(document).on('blur', '.discourse .thread textarea', function(e) {
    //clearReplyForms();
});

// When 'edit' is pressed, the comment is hidden and replaced with a form to edit it.
$(document).on('click', '.discourse .thread .controls .edit', function(e) {
    editComment($(e.target).closest('.comment'));
    e.preventDefault();
});

// When the down arrow or up arrow are pressed, a vote is cast.
$(document).on('click', '.discourse .thread .voting a', function(e) {
    var comment = $(e.target).closest('.comment');
    var target = $(e.target).closest('a');

    if ((target.hasClass('upvote') && target.hasClass('selected')) || (target.hasClass('downvote') && target.hasClass('selected'))) {
        voteComment(comment, 'reset');
    } else if (target.hasClass('upvote')) {
        voteComment(comment, 'up');
    } else if (target.hasClass('downvote')) {
        voteComment(comment, 'down');
    }
    e.preventDefault();
});


// Return all tags in the given text
function findAllTags(text) {
    var regex = /#(\w+)/g;
    var matches = [];
    while((match = regex.exec(text)) !== null){
        matches.push(match[1]);
    }
    return matches;
}

// Update the counts of tags on the page
function updateCounts(tag, prompt_id) {
    var total = $('.tag-count-' + tag);
    var value = (parseInt(total.text().substring(1)) || 0) + 1;
    total.text('(' + value + ')');
    
    var prompt = $('.tag-count-' + tag + '-' + prompt_id);
    var value = (parseInt(prompt.text().substring(1)) || 0) + 1;
    prompt.text('(' + value + ')');
}   



function clearForm(form) {
    form.find('textarea').val('');
    form.find('input[type=text]').val('');
    form.find('input[type=checkbox]').prop('checked', false);
    form.find('input[type=radio]').prop('checked', false);
    form.find('select').val('');
}


function formWaiting(form) {
    clearForm(form);
    form.find('input').attr('disabled', true);
    form.find('textarea').attr('disabled', true);
    form.find('select').attr('disabled', true);
}

function formReady(form) {
    form.find('input').attr('disabled', false);
    form.find('textarea').attr('disabled', false);
    form.find('select').attr('disabled', false);
}

function onMessageForm(e) {
    e.preventDefault();

    var form = $(this);
    var data = form.serialize();

    formWaiting(form);
    
    $.ajax({
        url: form.attr('action'),
        data: data,
        type: 'post',
        success: function(response) {
            formReady(form);

            postCommentSuccess(form, response);

            form.removeClass('editing');
        },
        error: function(response) {
            formReady(form);
            formError(form, response);
        }
    });
}

// When a message form is submitted, we should use ajax it.
$(document).on('submit', 'form.act-message', onMessageForm);


function formError(form, response) {
    console.log("ERROR", form, response);
}

function findStream(channel) {
    return $('.discourse.stream').filter(function() {
        return $(this).attr('data-channel') == channel;
    });
}

function realizeComment(message) {
    var source = $('<div>').append(message['html']).children().detach();

    var existing = $('#message-' + message.uuid);
    if (existing.length > 0) {
        existing.replaceWith(source);
        return source;
    }

    if (message.parent) {
        parent = $('.replies[for=message-' + message.parent + ']');
        parent.append(source);
    } else {
        var stream = findStream(message.url);
        source.prependTo(stream.find('.content'));
    }

    return source;

    var parent = $('#comment-' + comment.parent);

    if (source.length == 0) {
        var thread = findThread(comment.anchor);
        var prototype = thread.find('.comment.prototype').first();
        var source = prototype.clone().removeClass('prototype');
        
        if (parent.length == 0) {
            if (thread.find('.insert-comments-here').length > 0)
                thread.find('.insert-comments-here').before( source.show() );
            else
                thread.append(source.show());
        } else {
            var container = parent.closest('.subthread');
            if (container.length == 0) {
                container = parent.next('.subthread');
            }
            container.append(source.show());
        }

        source.addClass('created');
    } else {
        if ( source.hasClass('created') ) {
            return source;
        }
    }

    // Container
    source.attr('id', 'comment-' + comment.id);
    if (comment.deleted)
        source.addClass('deleted');
    else
        source.removeClass('deleted');

    // Meta
    source.find('.meta .score').empty().append(comment.value);
    source.find('.meta .voting a').removeClass('selected');
    if (comment.up)
        source.find('.meta .voting a.upvote').addClass('selected');
    if (comment.down)
        source.find('.meta .voting a.downvote').addClass('selected');

    if (comment.url)
        source.find('.meta .voting').attr('rel', comment.url)

    // Icon
    source.find('.user-icon').attr('href', comment.author.url || '#');
    source.find('.user-icon img').attr('src', comment.author.thumbnail || '/static/img/star.jpg')
                                 .attr('alt', comment.author.name)
                                 .attr('title', comment.author.name);

    // Body
    source.find('.info .body a').attr('href', comment.author.url || '#')
                                .empty()
                                .append(comment.author.name);
    source.find('.info .body .html').empty()
                                    .append(comment.html || comment.body);
    source.find('.info .body .text').empty()
                                   .append(comment.body);

    // Date
    source.find('.date')
          .attr('title', comment.created)
          .empty()
          .append(comment.naturaltime);

    // Controls
    if (comment.editable) {
        source.find('.controls .edit').show();
        source.find('.controls .delete').show();
    } else {
        source.find('.controls .edit').hide();
        source.find('.controls .delete').hide();
    }

    // Subthread
    if (!comment.parent) {
        source.after('<div class="subthread">');
    }

    return source;
}

function postCommentSuccess(form, result) {
    form[0].reset()
    var source = realizeComment(result);
    if (source.length > 0)
        source.scrollTo(500, 'swing', function() {
            source.fadeTo(250, 0).fadeTo(500, 1);    
        });
}

function deleteMessage(e) {
    e.preventDefault();
    var self = $(this).closest('.messages');
    var id = self.attr('id').substring('message-'.length);
    var url = self.closest('.stream').attr('data-channel');
    $.ajax({
        type: 'post',
        url: url,
        data: {'type': 'delete', 'parent': id},
        success: function() {
            self.fadeOut();
            $('*[for]').filter(function(i, item) {
                return ($(item).attr('for') == 'message-' + id);
            }).fadeOut();
        }
    });
}

function replyTo(comment) {
    var prototype = comment.closest('.thread').find('form').first();
    var subthread = comment.closest('.subthread');
    var reply_to = comment.attr('id').substring('comment-'.length);

    if (subthread.length == 0) {
        subthread = comment.next('.subthread');
    } else {
        reply_to = subthread.prev('.comment').attr('id').substring('comment-'.length);
    }

    var form = subthread.find('form');
    if (form.length == 0) {
        form = prototype.clone().addClass('temporary');
        form.find('[name=parent]').val(reply_to);
        form.find('[type=submit]').val("Add Reply");
        subthread.append( form );
    }
    
    form.find('textarea').focus();
    form.show();
}

function editComment(comment) {
    clearReplyForms();

    var prototype = comment.closest('.thread').find('form').first();
    var id = comment.attr('id').substring('comment-'.length);
    var text = comment.find('.text').html();

    comment.removeClass('created');

    form = prototype.clone().addClass('temporary');
    comment.hide().before(form);
    form.find('[name=id]').val(id);
    form.find('[type=submit]').val("Save Changes");
    form.find('textarea').val(text).focus();
}

function clearReplyForms() {
    $('.discourse .thread form.temporary').remove();
    $('.discourse .thread .comment').not('.prototype').show();
}

function voteComment(source, direction) {
    var url = source.find('.voting').attr('rel');
    if (!url) return;

    var score = source.find('.meta .score');

    source.find('.meta .voting a').removeClass('selected');

    if (direction == 'up')
        source.find('.meta .voting a.upvote').addClass('selected');
    else if (direction == 'down')
        source.find('.meta .voting a.downvote').addClass('selected');

    $.ajax({
        url: url,
        type: 'post',
        data: {'direction': direction},
        success: function(result) {
            score.empty().append(result);
        }
    });
}

function Stream(source) {
    var source = $(source);
    var existing = source.data('stream');
    if (existing) return existing;

    source.data('stream', this);
    this.source = source;

    this._filter = {
        type: this.source.attr('data-type').split(),
        tags: this.source.attr('data-tags').split(),
        template: this.source.attr('data-template'),
        sort: this.source.attr('sort')
    }

    this._original = $.extend({}, this._filter);
}

Discourse.stream = function(source) {
    return new Stream(source);
}

Stream.prototype.get_url = function() {
    return this.source.attr('data-channel');
}

Stream.prototype.reload = function(data) {
    if (this._loading) {
        this._loading.abort();
    }

    data = $.extend({
        'type': this._filter.type,
        'tags': this._filter.tags,
        'template': this._filter.template,
        'sort': this._filter.sort,
    }, data);
    
    this.source.fadeTo('fast', .5);

    this._loading = $.ajax({
        url: this.get_url(),
        data: data,
        success: $.proxy(this.success, this),
        error: $.proxy(this.error, this),
        complete: $.proxy(this.complete, this)
    });
}

Stream.prototype.success = function(data, textStatus, xhr) {
    this.source.html(data);
}

Stream.prototype.error = function(jqXHR, textStatus, errorThrown) {

}

Stream.prototype.complete = function(xhr, textStatus) {
    this._loading = null;
    this.source.fadeTo('fast', 1);
}

Stream.prototype.filter = function(filter) {
    $.extend(this._filter, filter);

    if (!this._filter.type || this._filter.type.length == 0) {
        this._filter.type = this.source.attr('data-type').split();
    }

    this.reload();
}

Stream.update = function(result) {
    console.log(result);
}

// When discourse tells us that there is a new comment
discourse.on('feedback', Stream.update);

$(document).on('change', 'form.discourse-stream-filter', function(e) {
    var form = $(this).closest('form');

    var tags = [];
    var type = [];

    $(this).find('input[type=checkbox]').each(function(i, item) {
        var item = $(item);
        if (item.prop('checked')) {
            if (item.attr('name') == 'tags') 
                tags.push($(item).attr('value'));
            else if (item.attr('name') == 'type') 
                type.push($(item).attr('value'));
        }
    });

    Discourse.stream( form.attr('for') ).filter({'tags': tags, 'type': type});
});


// Likes and Unlikes
Discourse.like = function(channel, uuid) {
    $.ajax({
        url: channel,
        data: {'type': 'like', 'parent': uuid},
        type: 'post',
        success: function(result) {
            var m = window.m = $('#message-' + result.parent);
            m.find('.likes').eq(0).empty().append(result.html).hide().fadeIn('fast');
        },
        error: function(response) {
            console.error(response);
        }
    });
}

$(document).on('click', '.act-like', function(e) {
    e.preventDefault();
    var a = $(this);
    var channel = a.closest('*[data-channel]').attr('data-channel');
    var uuid = a.attr('for');
    Discourse.like(channel, uuid);
    a.closest('.likes').empty();
});

Discourse.unlike = function(channel, uuid) {
    $.ajax({
        url: channel,
        data: {'type': 'unlike', 'parent': uuid},
        type: 'post',
        success: function(result) {
            var m = $('#message-' + result.parent);
            m.find('.likes').eq(0).empty().append(result.html).hide().fadeIn('fast');
        },
        error: function(response) {
            console.error(response);
        }
    });
}

$(document).on('click', '.act-unlike', function(e) {
    e.preventDefault();
    var a = $(this);
    var channel = a.closest('*[data-channel]').attr('data-channel');
    var uuid = a.attr('for');
    Discourse.unlike(channel, uuid);
    a.closest('.likes').empty();
});


$(document).on('change', 'form.sorter', function(e) {
    var form = $(this);
    var val = 'recent';
    form.find('input[type=radio]').each(function() {
        if ($(this).prop('checked')) {
            val = $(this).val();
        }
    });
    Discourse.stream($(this).attr('for')).filter({'sort': val});
});