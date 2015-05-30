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

// When 'delete' is pressed on a message, it is deleted.
$(document).on('click', '.discourse .messages .act-delete', deleteMessage);

// When 'reply' is pressed on a comment, the form is copied and added to the end of the subthread.
$(document).on('click', '.discourse .thread .controls .reply', function(e) {
    replyTo($(e.target).closest('.comment'));
    e.preventDefault();
});

// When 'edit' is pressed, the message content is hidden and replaced with a form to edit it.
$(document).on('click', '.discourse.stream .act-edit', function(e) {
    e.preventDefault();
    var source = $(e.target).closest('.messages');
    var value = $.parseJSON(unescape( $(e.target).attr('data-value') ));
    editMessage(source, value);
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
    form[0].reset();
}


function formWaiting(form) {
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

    if (this == window) {
        console.log("nope...", this);
        return;
    }

    var form = $(this);
    var data = form.serialize();

    formWaiting(form);
    
    $.ajax({
        url: form.attr('action'),
        data: data,
        type: 'post',
        success: function(response) {
            formReady(form);

            postMessageSuccess(form, response);

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

function postMessageSuccess(form, result) {
    form[0].reset()
    var source = Stream.update(result);
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

function editMessage(source, value) {
    console.log("editMessage", source[0], value);

    var type = value.form;
    var form = $('input[type=hidden][name=type][value=' + type + ']').eq(0).closest('form').clone().show().removeClass('hidden');

    source.find('.contents').children().hide();
    $('*[for=message-' + value.parent + ']').hide();

    source.find('.contents').append(form);

    focusForm(form);

    form.on('cancel', function() {
        form.remove();
        $('*[for=message-' + value.parent + ']').show();
        source.find('.contents').children().show();
    });

    source.find('[name]').each(function(i, item) {
        item = $(item);
        var k = item.attr('name');
        var v = value[k];
        if (item.attr('type') == 'radio' || item.attr('type') == 'checkbox') {
            item.prop('checked', item.attr('value') == v);
        } else {
            $(item).val(v);
        }
    });
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

    function getAttrArray(name) {
        return source.attr(name).split(/\s/).filter(function(item) { return item.length > 0 });
    }

    this._filter = {
        type: getAttrArray('data-type'),
        require_any: getAttrArray('data-any'),
        require_all: getAttrArray('data-all'),
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
        'require_any': this._filter.require_any,
        'require_all': this._filter.require_all,
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
        this._filter.type = this.source.attr('data-type').split(/\s/);
    }

    this.reload();
}

Stream.prototype.add = function(message) {
    // If the message has no html, ignore it.
    if (!message.html)
        return;

    var source = $('<div>').append(message['html']).children().detach();

    var existing = this.source.find('#message-' + message.uuid);
    if (existing.length > 0) {
        this.source.find('*[for=message-' + message.uuid + ']').remove();
        existing.replaceWith(source);
        return source;
    }

    if (message.parent) {
        if (message.type == 'like' || message.type == 'unlike') return;

        var parent = this.source.find('.replies[for=message-' + message.parent + ']');
        return source.appendTo(parent);
    }

    // We must filter the message to make sure it's the right type.
    if (!Stream.hasAnyType(message, this._filter.type))
        return;

    // We must filter the message to make sure it has the any of the require_any tags
    if (!Stream.hasAnyTag(message, this._filter.require_any))
        return;

    // We must filter the message to make sure it has the all of the require_all tags
    if (!Stream.hasAllTags(message, this._filter.require_all))
        return;

    this.source.find('.content').eq(0).prepend( source );
    return source
}

Stream.hasAnyType = function(message, types) {
    if (types.length < 1)
        return true;
    if ( $([message.type]).filter(types).length > 0 )
        return true;
    console.log("Not hasAnyType", message.type, types);
    return false;
}

Stream.hasAnyTag = function(message, tags) {
    if (tags.length < 1)
        return true;
    if ( $(message.tags).filter(tags).length > 0 )
        return true;
    console.log("Not hasAnyTag", message.tags, tags);
    return false;
}

Stream.hasAllTags = function(message, tags) {
    if (tags.length < 1)
        return true;

    if ( $(message.tags).filter(tags).length >= tags.length )
        return true;
    console.log("Not hasAllTags", message.tags, tags);
    return false;
}

Stream.update = function(message) {
    var source = $('.discourse.stream').filter(function(i, item) { return $(item).attr('data-channel-id') == message.channel });
    var stream = Discourse.stream( source );
    return stream.add(message);
}

// When discourse tells us that there is a new comment
discourse.on('message', Stream.update);

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

    Discourse.stream( form.attr('for') ).filter({'require_any': tags, 'type': type});
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
