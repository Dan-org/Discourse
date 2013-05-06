/*
    Toolbar for editing documents in discourse.
*/

Toolbar = Tea.Container.extend({
    type: 'discourse-toolbar',
    cls: 'discourse-toolbar',
    fadeDelay: 500,                 // Miliseconds to delay before fading when a document has lost focus.
    commands: [
        {slug: 'ul'},
        {slug: 'ol'},
        {slug: 'indent', key: 221},
        {slug: 'outdent', key: 219},

        {slug: 'bold', key: 'B'},
        {slug: 'italic', key: 'I'},
        {slug: 'strikethrough', key: 173},

        {slug: 'superscript', key: 54, icon: false},
        {slug: 'subscript', key: 53, icon: false},

        {slug: 'link', key: "K"},
        {slug: 'import', key: "M"}
    ],
    init : function() {
        this._keys = {};
        this.editor = null;
        this.__super__();
        this.source.appendTo(document.body).hide();
        
        jQuery.each(this.commands, jQuery.proxy(this.addCommand, this));
        
        this.hook($(document), 'keydown', this.onKeyDown);
    },
    open : function(editor) {
        this.editor = editor;
        this.source.stop(true, true).fadeIn('fast');
    },
    close : function(editor) {
        if (editor != this.editor) return;
        this.editor = null;
        this.source.stop(true, true).delay(this.fadeDelay).fadeOut();
    },
    onKeyDown : function(e) {
        if (!e.metaKey) return;
        if (!this.editor) return;

        var command = this._keys[e.keyCode];
        if (command) {
            this.execCommand(command);
            e.stopPropagation();
            return false;
        }
    },
    addCommand : function(index, command) {
        if (typeof(command.key) == 'string') {
            this._keys[command.key.charCodeAt(0)] = command;
        } else if (typeof(command.key) == 'number') {
            this._keys[command.key] = command;
        }

        this.addButton(index, command);
    },
    addButton : function(index, command) {
        if (command.icon == false) return;
        var icon = command.icon || command.slug;
        var button = this.append({
            type: 't-element',
            cls: 'button button-' + icon
        });

        var self = this;
        button.source.click(function(e) {
                self.execCommand(command);
                e.stopPropagation();
                return false;
            }).mousedown(function(e) {
                // Prevents focus being lost when clicking on this.
                e.preventDefault();          
            })
    },
    execCommand : function(command) {
        if (this.editor)
            this.editor.exec(command.slug);
    }
});