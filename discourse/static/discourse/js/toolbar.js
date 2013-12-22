/*
    Toolbar for editing documents in discourse.
*/

Toolbar = Tea.Container.extend({
    type: 'discourse-toolbar',
    cls: 'discourse-toolbar',
    fadeDelay: 500,                 // Miliseconds to delay before fading when a document has lost focus.
    commands: [
        {type: 'toolbar-group', commands: [
            {slug: 'p'},
            {slug: 'ul'},
            {slug: 'ol'},
            {slug: 'h', nodeName: 'h4'}
        ]},

        {slug: 'indent', key: 221},
        {slug: 'outdent', key: 219},

        {slug: 'bold', key: 'B'},
        {slug: 'italic', key: 'I'},
        {slug: 'strikethrough', key: 173},

        {slug: 'superscript', key: 54, invisible: true},
        {slug: 'subscript', key: 53, invisible: true},

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
        this.hook(editor, 'block', this.activateBlock);
        this.source.stop(true, true).fadeIn('fast');
    },
    close : function(editor) {
        if (editor != this.editor) return;
        this.editor = null;
        this.unhook(editor, 'block');
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
    addAccelerator : function(command) {
        if (typeof(command.key) == 'string') {
            this._keys[command.key.charCodeAt(0)] = command;
        } else if (typeof(command.key) == 'number') {
            this._keys[command.key] = command;
        }
    },
    addCommand : function(index, command) {
        this.addAccelerator(command);

        if (command.invisible) return;

        command.type = command.type || 'toolbar-button';
        var command = this.append(command);
        if (jQuery.isFunction(command.build))
            command.build();

        return command;
    },
    execCommand : function(slug) {
        if (this.editor)
            this.editor.exec(slug);
    },
    activateBlock : function(block) {
        if (block == null) return;
        this.items[0].activate(block.toLowerCase());
    }
});

Toolbar.addBlockStyle = function(config) {
    function execute(toolbar) {
        toolbar._parent.editor.command_blockquote(config.cls);
    }
    Toolbar.prototype.commands[0].commands.push({slug: config.slug, execute: execute});
}

ToolbarCommand = Tea.Element.extend({
    type: 'toolbar-button',
    cls: 'button',
    slug: null,
    key: null,
    init : function() {
        this.__super__();
        this.source.addClass('button-' + this.slug);
        this.source.click(jQuery.proxy(this.onClick, this));
        this.source.mousedown(function(e) { e.preventDefault() });
    },
    onClick : function(e) {
        if (this.execute) {
            this.execute(this._parent);
        } else {
            this._parent.execCommand(this.slug);
        }
        e.stopPropagation();
        return false;
    }
});

ToolbarGroup = Tea.Container.extend({
    type: 'toolbar-group',
    cls: 'button-group',
    build : function() {
        jQuery.each(this.commands, jQuery.proxy(this.addCommand, this));
        this.activate(this.commands[0].slug);
    },
    addCommand : function(index, command) {
        this._parent.addAccelerator(command);

        if (command.invisible) return;

        command.type = command.type || 'toolbar-button';
        command = this.append(command);
        if (jQuery.isFunction(command.build))
            command.build();

        return command;
    },
    activate : function(slug) {
        this.each(function(i, item) {
            if (item.slug == slug || item.nodeName == slug) {
                item.source.addClass('active');
            } else {
                item.source.removeClass('active');
            }
        })
    },
    execCommand : function(slug) {
        this.activate(slug);
        this._parent.execCommand(slug);
    }
});

ToolbarBlocktype = Tea.Container.extend({
    type: 'toolbar-blocktype',
    cls: 'toolbar-blocktype',
    __init__ : function() {
        this.append()
    },
    build : function() {
        jQuery.each(this.commands, jQuery.proxy(this.addCommand, this));
        this.setActive(this.commands[0].slug);
    },
    addCommand : function(index, command) {
        this._parent.addAccelerator(command);

        if (command.invisible) return;

        command.type = command.type || 'toolbar-button';
        command = this.append(command);
        if (jQuery.isFunction(command.build))
            command.build();

        return command;
    },
    setActive : function(slug) {
        this.each(function(i, item) {
            if (item.slug == slug) {
                item.source.addClass('active');
            } else {
                item.source.removeClass('active');
            }
        })
    }
})