Overlay = Tea.Container({
    cls: 'discourse-overlay',
    init : function() {
        this.__super__();
        $(jQuery.proxy(this.ready, this));
    },
    ready : function() {
        this.source.appendTo(document.body)
        this.toolbar = this.append('discourse-toolbar');
        this.linkEditor = this.append('discourse-link-editor');
        //this.imageEditor = this.append('discourse-image-editor');
            //this.status = this.append('discourse-status');
    },
    startEdit : function(node) {
        this.toolbar.open(node);
    },
    stopEdit : function(node) {
        this.toolbar.close(node);
        this.linkEditor.close();
    },
    editLink : function(a) {
        this.linkEditor.open(a);
    },
    importMedia : function(node) {
        return window.prompt("Image src", "http://");
    }
});

LinkEditor = Tea.Element.extend({
    type: 'discourse-link-editor',
    cls: 'discourse-link-editor',
    val_property: 'href',
    url_regex: /(\w+):\/?\/?(.+)/,
    init : function() {
        this.__super__();

        this.editing = null;
        
        this._text = $('<input type="text"></input>').appendTo(this.source);
        this._go = $('<a href="#">').appendTo(this.source);
        this._del = $('<a class="delete" href="#">').appendTo(this.source);

        this.source.hide();

        this.hook(this._text, 'keydown', this.onKeyDown);
        this.hook(this._go, 'click', this.go);
        this.hook(this._del, 'click', this.del);
    },
    open : function(a) {
        this.editing = a;
        var source = this.source;
        var pos = a.offset();
        source.stop(true, true)
              .css({top: pos.top - source.height(), left: pos.left, opacity: 0})
              .show()
              .animate({opacity: 100});

        var href = a.attr(this.val_property);
        if (href.substring(0, 7) == 'http://') {
            href = href.substring(7);
        }

        this._text.val(href)
                  .focus()
                  .select();
    },
    close : function() {
        if (this.editing) {
            this.editing.attr(this.val_property, this.getValue());
            this.editing = null;
            this.source.stop(true, true).delay(100).fadeOut();
        }
    },
    getValue : function() {
        var val = this._text.val();
        var m = val.match(this.url_regex);
        if (m) {
            val = m[1] + "://" + m[2];
        } else {
            val = "http://" + val;
        }
        return val;
    },
    onKeyDown : function(e) {
        if (e.keyCode == 13) {
            this.close();
            this._text.blur();
        } else if (e.keyCode == 27) {
            this.source.stop(true, true).delay(10).fadeOut(10);
            this.editing = null;
            this._text.blur();
        }
    },
    go : function() {
        window.open( this.getValue() );
        this.close();
    },
    del : function() {
        this.editing.contents().unwrap();
        this.close();
    }
});

MediaBrowser = Tea.Container.extend({
    type: 'discourse-media-browser',
    cls: 'discourse-media-browser',
    init : function() {
        
    },
    open : function(document) {
        
    }, 
    close : function() {
        this.hide();
    }
});

/*ImageEditor = LinkEditor.extend({
    type: 'discourse-image-editor',
    val_property: 'src',
    del : function() {
        this.editing.remove();
        this.close();
    }
});*/