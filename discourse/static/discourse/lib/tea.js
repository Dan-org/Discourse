/////////////////////////////////////////////////////////////// src/core.js //
/** Tea
    
    Complex UI framework based on jQuery.
    
    Copyright (c) 2012 Brantley Harris. All rights reserved.

 **/

(function() {
    var Tea = window.Tea = (window.Tea == undefined ?  {root: ''} : window.Tea);

    /** Tea.require(...)
        Imports the given arguments by appending <script> or <style> tags to the head.
        Note: Importing is done relative to the page we're on, not the script.
        Note: The required script is loaded sometime AFTER the requiring script, so you can't use
              the provided namespace (functions and variables) right away.
    
        arguments:
            Strings of urls to the given resource.  If the string ends with .css, it is added with
            a <style> tag; if it's a .js, it is added with a <script> tag.
     **/
    Tea.require = function()
    {
    	for(var i=0; i < arguments.length; i++)
    	{
    		var src = Tea.root + arguments[i];
    		if (Tea.require.map[src])
    			return;
    		Tea.require.map[src] = true;
    		try {
    			extension = src.match(/.*?\.(js|css)/i)[1];
    		} catch(e) { throw "Can only import .css or .js files, not whatever this is: " + src; }
    		if (extension == 'js')
    			document.write('<script type="text/javascript" src="' + src + '"></script>\n');
    		else if (extension == 'css')
    			document.write('<link rel="stylesheet" href="' + src + '" type="text/css"/>\n');
    	}
    }
    Tea.require.map = {}

    /** Tea.overrideMethod(super_function, function)
        Creates a callback that when run, provides a {{{__super__}}} on *this* which points to 
        {{{super_function}}}, and then runs {{{func}}}.  A great way to do inheritance.
     **/
    Tea.overrideMethod = function(super_func, func)
    {
        return function()
        {
            this.__super__ = function() { return super_func.apply(this, arguments) };
            var r = func.apply(this, arguments);
            delete this.__super__;
            return r;
        }
    }

    /** Tea.generateUniqueID(prefix)
        
        Generates a unique id with the given {{{prefix}}}.
     **/
    Tea.generateUniqueID = function(prefix) {
        if (!Tea._uniqueID)
            Tea._uniqueID = 1;
        return prefix + "-" + Tea._uniqueID++;
    }

    /// Types /////////
    Tea.types = {}

    /** Tea.registerType(name, object)
        Registeres an {{{object}}} as a type with the given {{{name}}}.
    
        name:
            Name of the type.
        
        object:
            The object.
     **/
    Tea.registerType = function(name, object) { Tea.types[name] = object; }


    /** Tea.getType(name)
        Returns the object registered with the given {{{name}}}.
     **/
    Tea.getType = function(name)
    { 
        return Tea.types[name];
    }


    /** Tea.create(options) 
        Returns an object created using the {{{options}}}, which can be an object 
        or a string.
    
        If {{{options}}} is a string, a type returned by {{{Tea.getType()}}} will 
        be returned, unless it can't find the type, then it is treated as a 
        jQuery object.
        
        If {{options}} is a jQuery object it is wrapped as the source of a 
        Tea.Element and returned.
    
        If {{{options}}} is an {{{Object}}}, the {{{.type}}} attribute will be
        used to look up the correct type and will be used to create an instance
        of that type.
    
        If {{{options}}} is an instance of a {{{Tea.Object}}}, it will be returned
        unaffected.
     **/
    Tea.create = function(options, extra) {
        if (options instanceof Tea.Object) return options;
        if (typeof(options) == 'string') {
            var t = Tea.getType(options);
            if (t)
                return t(extra);
            try {
                var jq = jQuery(options);
                options = jq;
            } catch(e) {}
        }
        if (options instanceof jQuery) {
            return Tea.create({type: 't-element', source: options}, extra);
        }
        if (options instanceof Object) {
            if (!options.type) throw "Tea.create() called with an object that has no type";
            var type = Tea.getType(options.type);
            if (!type) throw "Tea.create() called with unknown type: " + options.type;
            return type(jQuery.extend({}, options, extra));
        }
        throw "Tea.create() called with incorrect argument: " + options;
    }
    
    /// Tea.Object //////////
    var _creating = false;
    
    Tea.createInstance = function(Type) {
        _creating = true;
        var instance = new Type();
        //console.log('createInstance', instance, instance.constructor, Type);
        _creating = false;
        return instance;
    }
    
    Tea.extend = function(object, properties) {
        jQuery.each(properties, function(k, v) {
            if (jQuery.isFunction(v)) {
                var supr = object[k];
                if (jQuery.isFunction(supr))
                    v = Tea.overrideMethod(supr, v);
            }
            object[k] = v;
        });
    }
    
    Tea.extendType = function(SuperType, name, properties) {
        var Type = makeType(name);
        Type.supertype = SuperType;
        Type.prototype = Tea.createInstance(SuperType);
        Tea.extend(Type.prototype, properties);
        Type._name = name;
        Type.prototype.constructor = Type;
        Tea.registerType(name, Type);
        return Type;
    }
    
    function makeType(name) {
        var Type = function() {
            if (_creating) return this;
            return Type.create.apply(this, arguments);   
        }

        Type.name = name || "t-object";
        
        if (name) {
            Type.toString = function() {
                return "[type: " + name + "]";
            }
            Tea.registerType(name, Type);
        }
        
        Type.extend = function(properties) {
            properties = properties || {};
            return Tea.extendType(Type, properties.type, properties);
        }
        
        Type.create = function(options) {
            var instance = Tea.createInstance(Type);
            //console.log("create", instance, instance.constructor, Type, options);
            instance.__options__ = options || {};
            Tea.extend(instance, instance.__options__);
            instance.init(instance.__options__);
            return instance;
        }
        
        return Type;
    }
    
    /** Tea.Object

        Base object that allows class/subclass behavior, events, and a regard
        for "options".
        
        Mamal = Tea.Class({type: 'Mamal'});
        Human = Mamal.extend({type: 'Mamal'});
        Bob = Human({name: 'Bob'});
     **/
    Tea.Object = makeType("t-object");
    
    Tea.Object.prototype = {
        /** Tea.Object.init(options)
            
            Override this to change initialization code.
            
            Note: Not called on class prototypes.
        **/
        init : jQuery.noop,
        
        /** Tea.Object.toString()
        
            Returns a string representation of the object.
         **/
        toString : function()
        {
            return (this.constructor._name || "t-object");
        },
            
        /** Tea.Object.bind(event, handler, [args])
            Binds an event for this instance to the given function which will be 
            called with the given args.
    
            event:
                An event name to bind.
    
            handler:
                The function to call when the event is triggered.
    
            args (optional):
                A list of arguments to pass into when calling the handler.
         **/
        bind : function(event, handler, args)
        {
            if (!this.__events) this.__events = {};
            if (!this.__events[event]) this.__events[event] = [];
            this.__events[event].push([handler, args]);
        },
    
        /** Tea.Object.prototype.unbind(event, [handler])
            Unbinds an events from this instance.  If a handler is given, only 
            events pointing to that handler are unbound.  Otherwise all handlers 
            for that event are unbound.
    
            event:
                An event name to unbind.
    
            handler:
                Only events pointing the given handler are unbound.
         **/
        unbind : function(event, handler) { 
            if (!this.__events) return;
            var handlers = this.__events[event];
            if (!handlers) return;
            if (handler) {
                jQuery.each(handlers, function(i, pair) {
                    if (pair && pair[0] == handler) {
                        handlers.splice(i, 1);
                    }
                });
            } else {
                delete this.__events[event];
            }
        },

        /** Tea.Object.hook(target, event, handler, [args])
            Binds onto the target, but does so in a manner that allows this object
            to track its "hooks".  One can then unhook(target), or unhookAll() to
            release the bind.  This is beneficial from a memory standpoint, as
            hooks won't leak like a bind will.
        
            target:
                The target to bind onto.
        
            event:
                An event name to bind.
    
            handler:
                The function to call when the event is triggered.
    
            args (optional):
                A list of arguments to pass into when calling the handler.
         **/
        hook : function(target, event, func, args) {
            if (!this.__hooks) this.__hooks = [];
            var handler = jQuery.proxy(func, this);
            target.bind(event, handler, args);
            this.__hooks.push([target, event, handler]);
        },
    
        /** Tea.Object.unhook(target)
            Unhooks all binds on target.
        
            target:
                The target to release all binds from.
         **/
        unhook : function(target)
        {
            if (!this.__hooks) return;
            for(var i=0; i<this.__hooks.length; i++) {
                var hook = this.__hooks[i];
                if (target != hook[0]) continue;
                var event =   hook[1];
                var handler = hook[2];
                target.unbind(event, handler);
            }
        },
    
        /** Tea.Object.unhookAll()
            Unhooks all binds on all targets.
         **/ 
        unhookAll : function()
        {
            if (!this.__hooks) return;
            while(this.__hooks.length > 0) {
                var hook = this.__hooks.pop();
                var target =  hook[0];
                var event =   hook[1];
                var handler = hook[2];
                target.unbind(event, handler);
            }
        },
    
        /** Tea.Object.prototype.trigger(name)
    
            event:
                The event name to trigger.
        
            args:
                Arguments to pass onto the function.  These go after
                any arguments set in the bind().
         **/
        trigger : function(event, args) { 
            if (!this.__events) return;
            var handlers = this.__events[event];
            if (!handlers) return;
            if (!args) args = [];
            for(var i = 0; i < handlers.length; i++)
            {
                handlers[i][0].apply(this, (handlers[i][1] || []).concat(args));
            }
        },

        /** Tea.Object.prototype.destroy()
            
            Destroys the object and unhooks all events.
        **/
        destroy : function() {
            this.trigger('destroy');
            this.unhookAll();
        }
    }
    
    Tea.Class = Tea.Object.extend;
})();

//////////////////////////////////////////////////////////// src/element.js //
/** Tea.Element
    
    Copyright (c) 2012 Brantley Harris. All rights reserved.
 **/

Tea.Element = Tea.Class({
    type: 't-element',

    // Public
    source: '<div>',        // The source for this element, will be filtered through jQuery() when rendered, but can
                            // also be a function that returns a jQuery() object and takes the element as its argument.
    appendSourceTo: null,   // Append the source to this.
    value: null,            // This gets appended to the source when rendered.
    cls: null,              // Class to add to the source when rendered.
    hidden: false,          // Whether or not it is hidden.
    attr: null,             // Extra attributes to add when rendered.
    css: null,              // Extra css/style attributes to add when rendered.
    concrete: false,        // Whether or not the element has actually been added to the document dom. Until then
                            // one cannot expect it to have a proper width or height or other properties.

    // Private
    _parent: null,          // The parent element that "owns" this, when the parent gets destroyed, so does this.
    _children: null,        // Children elements, when this gets destroyed, so do the children.
    _orig_source: null,     // Set to the original source when rendered.

    // Methods
    init : function() {
        this.render();
        this.setup();
        if (this.value)
            this.setValue(this.value);
    },
    setup : function() {},
    render : function() {
        this._orig_source = this.source;

        if (jQuery.isFunction(this.source))
            this.source = this.source(this);
        
        var source = this.source = $(this.source);
        source.data("tea", this);

        if (this.cls)               source.addClass(this.cls);
        if (this.id)                source.attr('id', this.id);
        if (this.css)               source.css(this.css);
        if (this.attr)              source.attr(this.attr);
        if (this.hidden)            source.hide();
        if (this.appendSourceTo)    source.appendTo($(this.appendSourceTo));

        return source;
    },
    ready : function() {
        this.trigger('ready');
        this.concrete = true;
    },
    destroy : function() {
        this.source.remove();
        this.source = this._orig_source;
        this.concrete = false;
        if (this._parent)
            this._parent.disown(this);
        if (this._children) {
            for( var i = 0; i < this._children.length; i++) {
                this._children[i].destroy();
            }
        }
        this.__super__();
    },
    detach : function() { 
        this.source.detach();
    },
    hide : function()
    {
        this.setHidden(true);
    },
    show : function()
    {
        this.setHidden(false);
    },
    setHidden : function(flag)
    {
        if (flag)
            this.source.hide();
        else
            this.source.show();
    },
    findParent : function(type) {
        var now = this._parent;
        while(now) {
            if (now instanceof type) {
                return now;
            }
            now = now._parent;
        }
        throw new Error("Cannot find owner of the requested type");
    },
    findHandler : function(name) {
        var now = this._parent;
        while(now) {
            if (jQuery.isFunction(now[name]))
                return jQuery.proxy(now[name], now);
            now = now._parent;
        }
        return jQuery.noop;
    },
    setValue : function(v) {
        this.value = v;
        this.source.empty().append(v);
        return v;
    },
    getValue : function() {
        return this.value;
    },
    own : function(e)
    {
        if (e._parent === this)
            return e;

        e = Tea.create(e);

        if (e._parent)
            e._parent.disown(e);
        
        e._parent = this;

        if (!this._children)
            this._children = [];

        this._children.push(e);
        return e;
    },
    disown : function(e) {
        if (e._parent !== this) return;
        
        e._parent = null;
        this._children.splice(this._children.indexOf(e), 1);
        return e;
    },
    appendTo : function(source) {
        return this.source.appendTo(source);
    }
});

jQuery.fn.tea = function() {
    return this.data('tea');
}

////////////////////////////////////////////////////////// src/container.js //
/** Tea.Container
    
    An element that contains other elements.
    
    @requires Tea.Element

 **/

Tea.Container = Tea.Element.extend({
    type: 't-container',

    // Public
    items: null,        // Items within this container
    concrete: false,    // Elements added to a concrete container are automatically made concrete as well.

    // Private
    insertAfter: null,  // Item sources will be inserted after this for pos = 0,
    insertBefore: null, // otherwise it will be inserted before this for pos = 0,
    insertInto: null,   // otherwise, it will be inserted *into* this for pos = 0,

    init : function() {
        this.__super__();
        
        if (this.items) {
            var items = this.items;
            this.items = [];
            this.items = this.insertMany(0, items);
        } else {
            this.items = [];
        }

        if (this.value)
            this.setValue(this.value);
    },
    ready : function() {
        this.__super__();
        this.each(function(i, item) {
            item.ready();
        });
        this.refresh();
    },
    insertMany : function(pos, items) {
        var self = this;
        return jQuery.map(items, function(item, i) {
            return self.insert(pos + i, item);
        });
    },
    append : function(item)
    {
        return this.insert(this.items.length, item);
    },
    insert : function(pos, item)
    {
        if (typeof pos != 'number') throw new Error("First argument of insert(pos, item) must be an integer.");

        item = Tea.create(item);
        this.own(item);

        if (!this.items)
            this.items = [];

        if (pos < 0)
            pos = this.items.length + pos;
        if (pos < 0)
            pos = 0;

        if (pos >= this.items.length) {
            pos = this.items.length;
            if (this.items.length > 0)
                this.items[this.items.length-1].source.after(item.source);
            else if (this.insertAfter)
                this.insertAfter.after(item.source);
            else if (this.insertBefore)
                this.insertBefore.before(item.source);
            else if (this.insertInto)
                this.insertInto.append(item.source);
            else
                this.source.append(item.source);
            this.items.push(item);
            item._index = this.items.length-1;
        } else if (pos == 0) {
            // Note: there is deffinitely at least one element in this.items.
            this.items[0].source.before(item.source);
            this.items.unshift(item); 
            this.each(function(i, obj) {
                obj._index = i;
            });
        } else {
            this.items[pos-1].source.after(item.source);
            this.items.splice(pos, 0, item);
            this.each(function(i, obj) {
                obj._index = i;
            });
        }

        if (this.concrete)
            item.ready();

        this.refresh(item);

        return item;
    },
    prepend : function(item)
    {
        return this.insert(0, item);
    },
    remove : function(item)
    {
        if (item._parent !== this) return;
        this.items.splice(item._index, 1);
        this.disown(item);
        item.destroy();
        this.refresh();
    },
    disown : function(item) {
        if (item._parent !== this) return;
        this.items.splice(item._index, 1);
        this.__super__(item);
        this.refresh();
    },
    empty : function()
    {
        this.each(function(index, item) {
            item.destroy();
        });
        this.items = [];
        this.refresh();
    },
    each : function(func, context)
    {
        context = context || this;
        jQuery.each(jQuery.makeArray(this.items), function(i, item) {
            func.apply(context, arguments);
        });
    },
    setValue : function(value)
    {
        if (value == null || value == undefined) return;
        
        var fields = {};
        this.each(function(i, item) {
            if (item.name == '*')
                item.setValue(value);
            else if (item.name != undefined)
                fields[item.name] = item;
        });

        jQuery.each(value, function(k, v) {
            var item = fields[k];
            if (item) item.setValue(v);
        });
    },
    getValue : function()
    {   
        var gather = {};
        this.each(function(i, item) {
            if (item.name == '*')
                $.extend(gather, item.getValue());
            else if (item.name != undefined)
                gather[item.name] = item.getValue();
        });
        return gather;
    },
    refresh : function(new_item) {
        // Do layout, or whatever you want.  Is triggered after an item is removed / added and after ready();
        this.trigger('refresh', [new_item]);
    }
});

/////////////////////////////////////////////////////////////// src/form.js //
Tea.Field = Tea.Container.extend({
    type: 't-field',
    cls: 't-field',
    errors: null,
    hint: null,
    label: null,
    id: null,
    name: null,
    input: 't-text',
    validators: [],
    render : function() {
        var source = this.__super__();
        this.id = this.id || Tea.generateUniqueID('t-field');
        
        this._prompt = $('<label class="t-prompt"/>').appendTo(source);
        this._entry = $('<div class="t-entry"/>').appendTo(source);
        this._label = $('<div class="t-label"/>').appendTo(this._prompt);
        this._hint = $('<div class="t-hint"/>').appendTo(this._prompt);

        this.input = Tea.create(this.input);
        this.input.source.appendTo(this._entry);

        this._errors = $('<div class="t-errors"/>').appendTo(this._entry);

        this.setValue(this.value);
        this.setLabel(this.label);
        this.setHint(this.hint);
        this.setErrors(this.errors);
        return source;
    },
    destroy : function() {
        this.__super__();
        this.input.destroy();
    },
    setValue : function(v) {
        return this.input.setValue(v);
    },
    getValue : function() {
        return this.input.getValue();
    },
    setErrors : function(errors) {
        this.errors = errors;
        if (errors && errors.length) {
            this.source.addClass('t-has-errors');
            this._errors.empty().append(errors.join(" &middot; ")).show();
        } else {
            this.source.removeClass('t-has-errors');
            this._errors.empty().hide();
        }
    },
    getErrors : function() {
        return this.errors;
    },
    setLabel : function(html) {
        this.label = html;
        if (html == null) {
            this.source.addClass('t-no-label');
            this._label.empty().hide();
        } else {
            this.source.removeClass('t-no-label');
            this._label.empty().append(html).show();
        }
    },
    getLabel : function() {
        return this.label;
    },
    setHint : function(html) {
        this.hint = html;
        if (html) {
            this._hint.empty().append(html).show();
        } else {
            this._hint.empty().hide();
        }
    },
    validate : function() {
        var value = this.getValue();
        var errors = [];
        var self = this;
        jQuery.each(this.validators, function(i, validator) {
            var error = validator(value, self);
            if (error)
                errors.push(error);
        });
    }
})

Tea.Fieldset = Tea.Container.extend({
    type: 't-fieldset',
    cls: 't-fieldset',
    field: 't-field',
    source: '<fieldset/>',
    own : function(item) {
        var item = Tea.create(item);
        if (item instanceof Tea.Input) {
            return this.__super__({
                type: this.field,
                input: item,
                label: item.label || null,
                errors: item.errors || null,
                hint: item.hint || null,
                value: item.value || null,
                name: item.name || null
            })
        } else {
            var item = this.__super__(item);
            return item;
        }
    },
    validate : function() {
        
    },
    setErrors : function(errorMap) {
        this.each(function(i, item) {
            if (jQuery.isFunction(item.setErrors)) {
                item.setErrors(errorMap[item.name]);
            }
        });
    },
    getErrors : function() {
        var errorMap = {};
        this.each(function(i, item) {
            if (jQuery.isFunction(item.getErrors)) {
                errorMap[item.name] = item.getErrors();
            }
        });
        return errorMap;
    }
});

Tea.Form = Tea.Fieldset.extend({
    type: 't-form',
    cls: 't-form t-fieldset',
    action: ".",
    method: "post",
    source: '<form/>',
    submit: jQuery.noop,
    context: null,
    render : function() {
        var source = this.__super__();

        source.attr({
            action: this.action,
            method: this.method
        });

        this._submit = $('<input type="submit" class="t-submit t-hide"/>').appendTo(source);

        this.hook(source, 'submit', this.triggerSubmit);

        return source;
    },
    triggerSubmit : function(e) {
        return false;
        if (this.submit)
            return this.submit.call(this || this.context, e);
        else
            return true;
    }
});

///////////////////////////////////////////////////////////// src/button.js //
/** Tea.Button
    
    Click on me!
 **/

Tea.Button = Tea.Element.extend({
    type: 't-button',
    cls: 't-button',
    source: '<a>',
    text: '',
    icon: '',
    disabled: false,
    click: null,
    context: null,
    hasFocus: null,
    init : function()
    {
        this.__super__();
        
        this.setText(this.text);
        this.setIcon(this.icon);
        this.setDisabled(this.disabled);
    },
    render : function() {
        var source = this.__super__();

        this._icon = $('<div class="t-icon"/>').appendTo(source);
        this._text = $('<div class="t-text"/>').appendTo(source);

        source
            .bind('click', jQuery.proxy(this.handlePress, this))
            .bind('mousedown', jQuery.proxy(this.handleMouseDown, this))
            .bind('mouseup', jQuery.proxy(this.handleMouseUp, this))
            .bind('focus', jQuery.proxy(this.handleFocus, this))
            .bind('blur', jQuery.proxy(this.handleBlur, this))
            .hover(jQuery.proxy(this.handleHoverIn, this), jQuery.proxy(this.handleHoverOut, this));

        return source;
    },
    setText : function(txt) {
        this._text.empty().append(this.value = txt);
    },
    getText : function() {
        return this.value;
    },
    setValue : function(v) {
        this.setText(v);
    },
    setIcon : function(icon) {
        this.icon = icon;
        this._icon.attr('class', 't-icon ' + 'icon-' + icon);
    },
    getIcon : function() {
        return this.icon;
    },
    focus : function() {
        this.source.focus();
    },
    blur : function() {
        this.source.blur();
    },
    setFocus : function(flag) {
        if (flag)
            this.focus();
        else
            this.blur();
    },
    setDisabled : function(flag) {
        this.disabled = flag;

        if (flag) {
            this.source.addClass('disabled');
        } else {
            this.source.removeClass('disabled');
        }
    },
    disable : function() {
        this.setDisabled(true);
    },
    enable : function() {
        this.setDisabled(false);
    },
    handlePress : function() {
        if (this.disabled) return false;

        if (jQuery.isFunction(this.click))
            return this.click.call(this.context || this, this);

        if (typeof(this.click) == 'string')
            return this.findHandler(this.click).call(this.context || this, this);

        return true;
    },
    handleMouseDown : function() {
        if (!this.disabled)
            this.source.addClass('t-mouse-down');
    },
    handleMouseUp : function() {
        this.source.removeClass('t-mouse-down');
    },
    handleHoverIn : function() {
        if (!this.disabled)
            this.source.addClass('t-hover');
    },
    handleHoverOut : function() {
        this.source.removeClass('t-mouse-down');
        this.source.removeClass('t-hover');
    },
    handleFocus : function() {
        if (!this.disabled) {
            this.hasFocus = true;
            this.source.addClass('t-focus');
        }
    },
    handleBlur : function() {
        this.hasFocus = false;
        this.source.removeClass('t-focus');
    }
});

//////////////////////////////////////////////////////////// src/testing.js //
/** Tea.Testing !module

    @requires Tea

    A testing framework.
 **/

Tea.Testing = {};
Tea.Testing.suites = [];

try
{
    if (!jQuery.isFunction(console.log)) throw "!";
} catch(e) {
    console = {
        log : jQuery.noop,
        group : jQuery.noop,
        groupEnd : jQuery.noop,
        error: jQuery.noop,
        debug: jQuery.noop
    }
}

Tea.Testing.run = function(suite, test)
{
    Tea._testing = true;
    jQuery.ajaxSetup({async: false});
    
    var suites = Tea.Testing.suites;
    var count = 0;
    var passed = 0;
    
    for(var i = 0; i < suites.length; i++) 
    {
        if (suite && suites[i].name != suite) continue;
        
        var results = suites[i].run(test);
        count += results[0];
        passed += results[1];
    }
    
    if (count == passed)
        console.log("Passed.");
    else
        console.log("Failed. %s of %s passed.", passed, count);
    
    jQuery.ajaxSetup({async: true});
    Tea._testing = false;
    
    return {count: count, passed: passed};
}

Tea.Testing.fail = function(msg)
{
    var e = new Error(msg);
    e.failure = true;
    throw e;
}

function assertEqual(a, b, msg)
{
    if (a == b) return;
    if (a == undefined) a = 'undefined';
    if (b == undefined) b = 'undefined';
    Tea.Testing.fail( msg || ("assertEqual failed: " + a.toString() + ' != ' + b.toString()) );
}

function assert(a, msg)
{
    if (a) return;
    Tea.Testing.fail(msg || 'assertion failed.');
}

Tea.Testing.Suite = Tea.Class({
    type: 't-test-suite',
    name: null,
    init : function()
    {
        var tests = this._tests = [];
        
        if (!this.name)
            throw new Error("Unable to build test suite, it was not given a name attribute.");
        
        jQuery.each(this.__options__, function(k, v){
            if (!jQuery.isFunction(v)) return;
            if (k == 'teardown') return;
            if (k == 'setup') return;
            if (k == 'init') return;
            if (k == 'run') return;
            if (k[0] == '_') return;
            
            tests.push( Tea.Testing.Test({name: k, func: v}) );;
        });
        
        Tea.Testing.suites.push(this);
    },
    run : function(test)
    {
        this._passed = 0;
        
        console.group(this.name);
        
        if (this.setup)
        {
            try {
                this.setup.call(this);
            } 
            catch(e) {
                console.error('Error setting up suite.');
                console.error(e);
                console.groupEnd();
                return [1, 0];
            }
        }
        
        for(var i = 0; i < this._tests.length; i++)
        {
            if (test && this._tests[i].name != test) continue;
            
            this._tests[i].run(this, test == this._tests[i].name);
        }
        
        if (this.teardown)
        {
            try {
                this.teardown.call(this);
            } 
            catch(e) {
                console.error('Error tearing down suite.');
            }
        }
        
        if (this._passed == this._tests.length)
            console.log("All of %s passed.", this._tests.length);
        else
            console.log("%s of %s passed.", this._passed, this._tests.length);
        
        console.groupEnd();
        
        return [this._tests.length, this._passed];
    }
});

Tea.Testing.Test = Tea.Class({
    type: 't-test',
    name: null,
    func: null,
    init : function()
    {
        this.status = null;
        this.comment = null;
    },
    run : function(suite, let)
    {
        try
        {
            this.func.call(suite);
            this.status = '.';
            suite._passed += 1;
        } 
        catch(e)
        {
            pass = false;
            
            if (let)
                throw e;
            
            if (e.failure)
            {
                this.status = 'F';
                this.comment = e.message;
                console.error("%s Failed - %s: %s\n", this.name, e.name, e.message, Tea.Testing.trace(e));
            }
            else
            {
                this.status = 'E';
                this.comment = e.message;
                console.error("%s Threw - %s: %s\n", this.name, e.name, e.message, Tea.Testing.trace(e));
            }    
        }
    }
});

Tea.Testing.trace = function(e)
{
    if (!e.stack)
        return e.sourceURL + ":" + e.line;
    
    var split = e.stack.split('\n');
    var frames = [];
        
    for(var i = 0; i < split.length; i++)
    {
        var frame = split[i];
        frames.push( frame.split('@').reverse().join(" - ") );
    }
    
    return frames.join("\n");
}

Tea.Testing.setupAjax = function(responses)
{
    Tea.Testing.ajaxCalls = [];
    Tea.Testing._ajax = jQuery.ajax;
    
    jQuery.ajax = function(options)
    {
        Tea.Testing.ajaxCalls.push(options);
        try {
            var response = responses[options.url](options);
        } catch (e) {
            console.error("Unable to find url in the responses: %s", options.url);
            throw e;
        }
        
        options.success.call(this, response);
    }
}

Tea.Testing.teardownAjax = function()
{
    jQuery.ajax = Tea.Testing._ajax
}

/////////////////////////////////////////////////////////////// src/tree.js //
/** Tea.Tree

    A Tree item, buttons with containers on the back.
    
    @extends Tea.Button
 **/

Tea.Tree = Tea.Button.extend({
    type: 't-tree',
    cls: 't-tree t-button',
    items: null,
    expanded: false,
    render : function() {
        var source = this.__super__();
        this.tick = jQuery('<div class="t-tick"/>').prependTo(source);
        this.tick.bind('click', jQuery.proxy(this.handleTick, this));
        this.tail = Tea.create({type: 't-container', cls:'t-tail', items: this.items});
        this.tail.hook(this, 'remove', this.tail.remove);
        this.tail.render().appendTo(source);
        this.tail._parent = this;
        if (!this.expanded)
            this.collapse()
        else
            this.expand();
        return source;
    },
    expand : function() {
        this.expanded = true;
        this.source.addClass('t-expanded');
        this.source.removeClass('t-collapsed');
    },
    collapse : function() {
        this.expanded = false;
        this.source.removeClass('t-expanded');
        this.source.addClass('t-collapsed');
    },
    toggleExpanded : function() {
        if (this.expanded)
            this.collapse();
        else
            this.expand();
    },
    handleTick : function(e) {}
});

////////////////////////////////////////////////////////////// src/input.js //
Tea.Input = Tea.Element.extend({
    type: 't-input',
    source: '<input type="text"/>',
    cls: 't-input',
    value: "",
    placeholder: null,
    name: null,
    render : function() {
        var source = this.__super__();

        if (this.name)
            this.source.attr('name', this.name);
        if (this.placeholder)
            this.source.attr('placeholder', this.placeholder);

        return source;
    },
    getValue : function() {
        return this.source.val();
    },
    setValue : function(v) {
        this.source.val(v);
    },
    focus : function() {
        return this.source.focus();
    },
    blur : function() {
        return this.source.blur();
    }
});

Tea.PasswordInput = Tea.Input.extend({
    type: 't-password',
    cls: 't-password',
    source: '<input type="password"/>'
});

Tea.SubmitInput = Tea.Input.extend({
    type: 't-submit',
    cls: 't-submit',
    source: '<input type="submit"/>'
});

Tea.ButtonInput = Tea.Input.extend({
    type: 't-button-input',
    cls: 't-button-input',
    source: '<input type="button"/>'
});

Tea.TextArea = Tea.Input.extend({
    type: 't-textarea',
    cls: 't-textarea',
    source: '<textarea/>',
    getValue : function() {
        return this.source.html();
    },
    setValue : function(v) {
        this.source.empty().append(v);
    }
});

Tea.Checkbox = Tea.Input.extend({
    type: 't-checkbox',
    cls: 't-checkbox',
    source: '<input type="checkbox">',
    getValue : function() {
        return this.source.prop('checked');
    },
    setValue : function(v) {
        return this.source.prop('checked', v ? true : false);
    }
});

Tea.Select = Tea.Input.extend({
    type: 't-select',
    cls: 't-select',
    source: '<select>',
    options: null,
    render : function() {
        var source = this.__super__();

        this.setOptions(this.options);

        return source;
    },
    setOptions : function(options) {
        this.source.empty();
        if (!options) return;
        options = $.makeArray(options);

        var self = this;
        jQuery.each(this.options, function(i, item) {
            self.addOption(item);
        });
    },
    addOption : function(option) {
        var value = null;
        var label = null;
        if (option instanceof Array) {
            if (option.length == 1) {
                value = label = option[0];
            } else {
                value = option[0];
                label = option[1];
            }
        } else if (typeof(option) == 'string') {
            value = label = option;
        } else {
            value = option.value;
            label = option.label;
        }

        var option = this.createOption(value, label);
        this.source.append( option );
    },
    createOption : function(value, label) {
        var option = $('<option/>');
        option.append(label)
        option.attr('value', value);
        return option;
    },
    getValue : function() {
        return this.source.find('option').eq(this.source.prop('selectedIndex')).prop('value');
    },
    getLabel : function(value) {
        // Returns the label for the value, or if value is not specified returns the label of the current value.
        var result = null;
        if (value == null)
            value = this.getValue();
        this.source.find('option').each(function(i, item) {
            if (item.value == value) {
                result = $(item).html();
                return false;
            }
        });
        return result;
    },
    setValue : function(v) {
        v = v.toString();
        var source = this.source;
        source.find('option').each(function(i, item) {
            if (item.value == v) {
                source[0].selectedIndex = i;
                return false;  // Stops the each() loop
            }
        });
    }
});

////////////////////////////////////////////////////////////// src/stack.js //
/** Tea.Stack

    A container that acts as a stack, you can push and pop onto it.
    
    The default skin pushes elements onto it from the right to the left, so
    that you only see the top few elements that can fit on the screen.
    
    @requires Tea.Container
    @extends Tea.Container
 **/

Tea.Stack = Tea.Container.extend({
    type: 't-stack',
    cls: 't-stack',

    // Public 
    margin: 6,

    // Private
    _paused: false,

    // Methods
    ready : function() {
        this.__super__();
        $(window).resize(jQuery.proxy(this.refresh, this));
    },
    own : function( item )
    {
        var item = this.__super__(item);
        this.hook(item, 'close', function() {
            this.pop(item);
        });
        return item;
    },
    /** Tea.Stack.push(item, [after])
        
        Pushes the *item* onto the stack.
        
        If *after* is specified, all items after it will be popped before
        pushing the *item*.
    **/
    push : function( item, after )
    {   
        if (after)
        {
            this.pause();
            this.popAfter(after);
            this.play();
        }

        return this.append(item);
    },
    /** Tea.Stack.pop( [item] )
        
        Pops the top item off the stack.
        
        If *item* is specified, it will pop that item and all after it.
    **/
    pop : function( item )
    {
        this.pause();
        
        if ( item )
            this.popAfter( item );
        else
            item = this.items[this.items.length-1];
        
        this.remove(item);
        this.play();
        return item;
    },
    popAfter : function( item )
    {
        if (item._parent !== this) return;
        
        this.pause();
        
        while(this.items.length > item._index + 1) {
            this.remove(this.items[item._index + 1]);
        }
        
        this.play();
    },
    pause : function()
    {
        this._paused += 1;
    },
    play : function()
    {
        this._paused -= 1;
        if (this.paused <= 0) {
            this.paused = 0;
            this.refresh();
        }
    },
    refresh : function(new_item) {
        this.__super__();

        if (!this.concrete) return;
        if (this._paused > 0) return;

        var max_width = this.source.width();
        var gutter = this.margin;
        var width = this.margin;
        
        var show = 0;
        
        for(var i = this.items.length-1; i >= 0; i--) {
            var item = this.items[i];
            var w = item.source.width() + gutter;
            if (width + w > max_width && show > 0)
                break;
            width += w;
            show += 1;
        }
        
        var start = this.items.length - show;
        var left = gutter;
        
        this.each(function(index, item) {
            if (index < start) {
                item.source.hide().css('left', 0 - item.source.width() - gutter);
                return;
            }
            
            if (item == new_item)
                item.source.css({
                  left: left,
                  opacity: 0,
                });

            item.source
                .stop(true, true)
                .show()
                .css('position', 'absolute')
                .animate({
                    left: left,
                    opacity: 1
                });
            
            left += (item.source.width() + gutter);
        });
    }
});

////////////////////////////////////////////////////////////// src/utils.js //
/** Tea.latent(func, milliseconds, context)
    Calls the given function {{{func}}} after the given {{{milliseconds}}} with
    a {{{this}}} of {{{context}}}.
    
    The function returned is a wrapper function.  When it is called, it waits 
    for the specified {{{milliseconds}}} before actually being run.  Also, if
    it is waiting to run, and is called again, it will refresh its timer.
    This is great for things like auto-complete, where you want to cancel and
    refresh the timer every time a key is hit
    
    You can easily bind a latent to an event, the following code will run 
    the method "onKeyup" on "this" 300 milliseconds after the last keyup event 
    of a series:
    
    {{{ $(window).keyup( Tea.latent(this.onKeyup, 300, this) )}}}
    
    The function returned also provides a few extra methods on the function,
    itself:
    
    {{{.cancel()}}} - Cancels the timer.
    
    {{{.refresh([milliseconds])}}} - Refreshes the timer, and optionally resets the
    {{{milliseconds}}}.
    
    Example:
    {{{
    function hello() {
        this.log("Hello World!");
    }
    
    hello = latent(hello, console, 1000);
    hello();
    hello();
    hello();
    
    // After 1 second: "Hello World!"
    
    hello();
    hello.cancel();
    
    // Nothing...
    
    hello.refresh(1000);
    
    // After 1 second: "Hello World!"
    
    hello();
    
    // After 1 second: "Hello World!"
    }}}
 **/
 
Tea.latent = function(func, milliseconds, context)
{
    var timeout = null;
    var args = null;
    context = context || this;
    
    function call()
    {
        clearTimeout(timeout);
        timeout = null;
        func.apply(context, args);
    }
    
    function refresh(new_milliseconds)
    {
        milliseconds = new_milliseconds || milliseconds;
        if (timeout)
            clearTimeout(timeout);
        timeout = setTimeout(call, milliseconds)
    }
    
    function trip()
    {
        call();
        refresh();
    }
    
    function cancel()
    {
        if (timeout)
            clearTimeout(timeout);
        timeout = null;
    }
    
    var self = function()
    {
        args = arguments;
        refresh();
    }
    
    self.trip = trip;
    self.call = call;
    self.refresh = refresh;
    self.cancel = cancel;
    
    return self;
}

////////////////////////////////////////////////////////////// src/panel.js //
Tea.Panel = Tea.Container.extend({
    type: 't-panel',
    title: '',
    closable: false,
    fill: true,
    render : function() {
        source = this.__super__();

        this.top = this.own({type: 't-container', cls: 't-top-bar t-bar', items: this.top});
        this.bottom = this.own({type: 't-container', cls: 't-bottom-bar t-bar', items: this.bottom});

        this._title = $('<div class="t-title">').append(this.title).appendTo(source);
        this._closer = $('<a class="t-closer">').append('Close').appendTo(source);
        this.top.source.appendTo(source);
        this._content = $('<div class="t-content">').appendTo(source);
        this.bottom.source.appendTo(source);

        this.insertInto = this._content;

        return source;
    },
    setTitle : function(title)
    {
        this.title = title;
        this._title.empty().append(title);
    },
    getTitle : function()
    {
        return this.title;
    },
    close : function()
    {
        this.trigger('close');
    },
    onClose : function() {
        this.close();
    }
});

/*
Tea.Panel({
    items: [
        {type: 't-title', text: 'Hello'},
        {type: 't-closer', text: ''},
        {type: 't-menu-bar', items: ['save'], name: null},
        {type: 't-content', text: '', fill: 'vertical'},
        {type: 't-menu-bar', items: ['save'], name: null},
    ],
    onClose : function() {
        this.trigger('close');
    },
    onSave : function() {

    }
})*/

