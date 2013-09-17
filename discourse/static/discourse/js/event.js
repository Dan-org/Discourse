Discourse = function(url) {
    this.toSend = [];
    this.connected = false;

    if (window.io == undefined) {
        this.socket = null;
        this.on = this.send = this.follow = $.noop;
    } else {
        this.socket = io.connect(url);
        this.on = jQuery.proxy(this.socket.on, this.socket);
    }

    this.on('connect', jQuery.proxy(this.onConnect, this));
}

$.extend(Discourse.prototype, {
    on : function(name, func) {
        return this.socket.on(name, func);
    },
    send : function() {
        if (!this.connected) return this.toSend.push(arguments);
        this.socket.emit.apply(this.socket, arguments);
    },
    onConnect : function() {
        this.connected = true;
        while (this.toSend.length > 0) {
            this.socket.emit.apply(this.socket, this.toSend.shift());
        }
    },
    follow : function(path) {
        return this.send("follow", path);
    },
    bind : function(name, func) {
        return this.socket.on(name, func);
    },
    unbind : function(name, func) {
        this.socket.removeListener(name, func);
    }
});

window.discourse = new Discourse('/discourse');