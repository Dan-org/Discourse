/*
Status
    info("failure", "Error with doing things.", 5000);
    info("success", "Save success.", 1000);
    info("working", "Saving Document...", 0);
*/

Document = Tea.Element.extend({
    type: 'discourse-document',
    storage: null,
    init : function() {
        this.__super__();
        this.editing = false;
        if (!this.storage)
            this.storage = Storage({ document: this,
                                     url: this.source.attr('url'),
                                     attribute: this.source.attr('attribute'),
                                     value: this.getValue(),
                                     clean: (this.source.attr('clean') ? this.source.attr('clean') : null)});

        this.hook($(document), 'click', this.onDocClick);
        this.hook($(document), 'unload', this.stopEditing);
        this.hook(this.source, 'click', this.onClick);
        this.hook(this.source, 'keydown', this.onKeyDown);
        this.hook(this.source, 'input', this.onInput);

        if (this.is_empty()) {
            return this.source.addClass('discourse-empty').empty();
        } else {
            this.source.removeClass('discourse-empty');
        }
    },
    startEditing : function() {
        Overlay.startEdit(this);
        this.source.attr('contenteditable', true)
                   .addClass('discourse-editing')
                   .removeClass('discourse-empty')
                   .focus();

        this.collapseRepr();

        if (this.is_empty()) {
            this.cursorSanityCheck();
        }
        this.editing = true;
    },
    stopEditing : function() {
        Overlay.stopEdit(this);
        
        this.sanitize();

        if (this.is_empty()) {
            this.source.addClass('discourse-empty').empty();
        } else {
            this.source.removeClass('discourse-empty');
        }

        this.source.attr('contenteditable', false)
                   .removeClass('discourse-editing');
        this.storage.setValue(this.getValue());
        this.storage.save();

        this.expandRepr();
        this.editing = false;
    },
    collapseRepr : function() {
        var map = this._repr = {};
        this.source.find('*[repr]').each(function(i, element){
            var e = $(element);
            var name = e.attr('repr');
            var repr = $('<div class="repr">' + name + "</div>");
            map[name.trim()] = e.replaceWith(repr);
        });
    },
    expandRepr : function() {
        map = this._repr;
        this.source.find('.repr').each(function(i, element) {
            var e = $(element);
            var name = e.html().trim();
            var source = map[name];
            if (source) {
                e.replaceWith(source);
            }
        });
    },
    onDocClick : function(e) {
        var in_document = ( e.target == this.source[0] || 
                            jQuery.contains(this.source[0], e.target) );
        var in_overlay  = ( e.target == Overlay.source[0] ||
                            jQuery.contains(Overlay.source[0], e.target) );
        if (in_document && !this.editing) {
            this.startEditing();
            if (e.target.nodeName == 'A') {
                Overlay.editLink($(e.target));
            }
            if (e.target.nodeName == 'IMG') {
                //Overlay.editImage($(e.target));
            }
        } else if (this.editing && !in_document && !in_overlay) {
            this.stopEditing();
        } else if (in_document && this.editing && e.target.nodeName == 'A') {
            Overlay.editLink($(e.target));
        } else if (in_document && this.editing && e.target.nodeName == 'IMG') {
            //Overlay.editImage($(e.target));
        }
    },
    onKeyDown : function(e) {
        // If you tab, that means you leave focus
        if (e.keyCode == 9) this.stopEditing();
    },
    onInput : function(e) {
        if (this.editing) {
            this.sanitize();
            this.cursorSanityCheck();
            this.storage.setValue(this.getValue());
        }
    },
    getValue : function() {
        return this.source.html().trim();
    },
    setValue : function(v) {
        this.source.html(v);
    },
    exec : function(name) {
        return this['command_' + name]();
    },
    command_ul: function() { document.execCommand("insertUnorderedList"); this.sanitize(); },
    command_ol: function() { document.execCommand("insertOrderedList"); this.sanitize(); },
    command_indent: function() { document.execCommand("indent"); this.sanitize(); },
    command_outdent: function() { document.execCommand("outdent"); this.sanitize(); },
    command_bold: function() { document.execCommand("bold") },
    command_italic: function() { document.execCommand("italic") },
    command_strikethrough: function() { document.execCommand("strikethrough") },
    command_subscript: function() { document.execCommand("subscript") },
    command_superscript: function() { document.execCommand("superscript") },
    command_link: function() { 
        document.execCommand("createLink", false, 'http://example.com');
        var a = $(window.getSelection().focusNode.parentNode);
        Overlay.editLink(a);
    },
    command_import: function() {
        //document.execCommand("insertHTML", false, '<img width="50" height="50" src=""/>');
        var media_src = Overlay.importMedia(this);
        if (media_src)
            document.execCommand("insertHTML", false, '<img src="' + media_src + '"/>');
    },
    is_empty : function() {
        return (this.source.text().trim() == '' && this.source.find('image').length == 0);
    },
    sanitize : function() {
        var src = this.source;

        // Unwrap unnatural structures.
        while(src.find('p p').length > 0) { src.find('p p').unwrap(); }
        while(src.find('p ul').length > 0) { src.find('p ul').unwrap(); }
        while(src.find('p ol').length > 0) { src.find('p ol').unwrap(); }

        // Get rid of orphaned li tags.
        src.children('li').contents().unwrap();
        
        // Tags allowed to be in the first level.
        var first_level = ['p', 'header', 'blockquote', 'ul', 'ol', 'div'];

        // Remove style tags on blackquotes / paragraphs, wtf.
        src.find('p').attr('style', null);
        src.find('blockquote').attr('style', null);

        // Remove tags that are banned
        $("span").each(function(){
            $(this).replaceWith($(this).html());
        });
        
        // Move all orphans into a paragraph.
        var orphans = [];
        src.contents().each(function(i) {
            if (!this.tagName || $.inArray(this.tagName.toLowerCase(), first_level) < 0) {
                orphans.push(this);
            } else if (orphans.length > 0) {
                $('<p>').append(orphans).insertBefore(this);
                orphans = [];
            }
        });
        if (orphans.length > 0) {
            $('<p>').append(orphans).appendTo(src);
        }
    },
    cursorSanityCheck : function() {
        var src = this.source;

        // Ensures the cursor that there is at least one block object.
        if (src.children().length == 0) {
            var p = $("<p>&nbsp;</p>");
            this.source.empty().append(p);
            this.selectAllChildren( p );
            return;
        }

        // Check if our selection outside of a block, if so put it in the first child.
        var sel = window.getSelection();
        if ( sel.anchorNode == src[0] ) {
            var range = document.createRange();
            range.selectNodeContents(src.children()[0]);
            range.collapse(false);
            sel.removeAllRanges(); //(sel.getRangeAt(0));
            sel.addRange(range);
        }
    },
    insert : function(src) {
        window.getSelection();
    },
    selectAllChildren : function(obj) {
        window.getSelection().selectAllChildren(obj[0]);
    }
});

