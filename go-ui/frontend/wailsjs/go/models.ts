export namespace backend {
	
	export class PythonManager {
	
	
	    static createFrom(source: any = {}) {
	        return new PythonManager(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	
	    }
	}

}

export namespace ui {
	
	export class Provider {
	    name: string;
	    models: string[];
	    available: boolean;
	
	    static createFrom(source: any = {}) {
	        return new Provider(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.name = source["name"];
	        this.models = source["models"];
	        this.available = source["available"];
	    }
	}
	export class TaskRequest {
	    type: string;
	    message: string;
	    provider: string;
	    model: string;
	
	    static createFrom(source: any = {}) {
	        return new TaskRequest(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.type = source["type"];
	        this.message = source["message"];
	        this.provider = source["provider"];
	        this.model = source["model"];
	    }
	}

}

