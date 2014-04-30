StatusBox = Tea.Container.extend({
    type: 'discourse-status-box',
    cls: 'discourse-status-box',
    limit: 5,
    init : function() {
        this.__super__();
        this.source.appendTo('.discourse-overlay');
    },
    message : function(options) {
        if ($(window).width() < 500)
            this.clearLast();

        options = $.extend({
            type: 'discourse-status-message'
        }, options);

        return this._last = this.append(options);
    },
    confirm : function(title, text) {
        return this.message({
            title: title,
            text: text,
            level: 'confirm'
        });
    },
    alert : function(title, text) {
        return this.message({
            title: title,
            text: text,
            level: 'alert'
        });
    },
    info : function(title, text) {
        return this.message({
            title: title,
            text: text,
            level: 'info'
        });
    },
    error : function(title, text) {
        return this.message({
            title: title,
            text: text,
            level: 'error'
        });
    },
    progress : function(title, value) {
        if (this._progress && this._progress._open) {
            this._progress.setTitle(title);
            this._progress.setValue(value || 0);
        }
        else
            this._progress = this.message({
                type: 'discourse-status-progress',
                title: title,
                value: value || 0,
            })
    },
    clearLast : function() {
        if (this._last && this._last)
            this._last.destroy();
    }
});

StatusMessage = Tea.Element.extend({
    type: 'discourse-status-message',
    cls: 'message',
    level: 'info',
    death: 2200,
    init : function() {
        this.__super__();
        this._open = true;
        this._timeout = null;
        this._close = $('<div class="close">');

        source = this.source;
        
        source
            .addClass("status-" + this.level)
            .append($('<div class="title">').append(this.title))
            .append($('<div class="text">').append(this.text || '&nbsp;'))
            .append(this._close)
            .css('opacity', 0)
            .animate({'opacity': .85}, 500)
        
        this.hook(source, 'click', this.click);
        this.hook(this._close, 'click', this.destroy);

        if ($(window).width() < 500 && this.death) {
            this.dieSoon();
        } else if (this.death) {
            $(window.document).one('mousemove keydown click touchstart scroll', jQuery.proxy(this.dieSoon, this));
        }
    },
    setTitle : function(src) {
        this.title = src;
        this.source.find('.title').empty().append(src || '&nbsp;');
    },
    setText : function(src) {
        this.text = src;
        this.source.find('.text').empty().append(src || '&nbsp;');
    },
    die : function(time) {
        this._timeout = setTimeout(jQuery.proxy(this.hide, this), time);
    },
    dieSoon : function() {
        this.die(this.death);
    },
    click: function() {
        this.destroy();
    },
    hide : function() {
        this._open = false;
        if (this.source.fadeOut)
            this.source.fadeOut(1000, 'swing', jQuery.proxy(this.destroy, this));
    },
    destroy : function() {
        this._open = false;
        if (this._timeout)
            clearTimeout(this._timeout)
        this._timeout = null;
        this.__super__();
    }
});

StatusProgress = StatusMessage.extend({
    type: 'discourse-status-progress',
    level: 'progress',
    value: 0,
    init : function() {
        this._progress = $('<div class="progress-bar"/>');
        this._value = $('<div class="progress-value"/>').appendTo(this._progress);
        this.__super__();
        this.source.append(this._progress);
        this.setValue(this.value);
    },
    setValue : function(v) {
        if (v < 0) v = 0;
        if (v > 1) v = 1;
        this.value = v;
        this._value.stop().animate({'width': v * 100 + "%"});
        this.dieSoon();
    },
    dieSoon : function() {
        if (this.value < 1)
            return;
        return this.__super__();
    }
});

