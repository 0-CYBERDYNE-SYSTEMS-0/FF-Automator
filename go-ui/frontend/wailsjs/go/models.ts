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
	
	export class ChatMessage {
	    role: string;
	    content: string;
	
	    static createFrom(source: any = {}) {
	        return new ChatMessage(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.role = source["role"];
	        this.content = source["content"];
	    }
	}
	export class Automation {
	    id: string;
	    name: string;
	    description: string;
	    task: string;
	    category: string;
	    tags: string[];
	    llm_provider: string;
	    llm_model: string;
	    custom_system_message?: string;
	    conversation_history: ChatMessage[];
	    created_at: string;
	    execution_count: number;
	    success_count: number;
	    failure_count: number;
	    last_executed_at: string;
	    runtime_parameters?: Record<string, any>;
	
	    static createFrom(source: any = {}) {
	        return new Automation(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.id = source["id"];
	        this.name = source["name"];
	        this.description = source["description"];
	        this.task = source["task"];
	        this.category = source["category"];
	        this.tags = source["tags"];
	        this.llm_provider = source["llm_provider"];
	        this.llm_model = source["llm_model"];
	        this.custom_system_message = source["custom_system_message"];
	        this.conversation_history = this.convertValues(source["conversation_history"], ChatMessage);
	        this.created_at = source["created_at"];
	        this.execution_count = source["execution_count"];
	        this.success_count = source["success_count"];
	        this.failure_count = source["failure_count"];
	        this.last_executed_at = source["last_executed_at"];
	        this.runtime_parameters = source["runtime_parameters"];
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}
	export class AutomationHistory {
	    execution_id: string;
	    executed_at: string;
	    status: string;
	    duration: number;
	    error_message?: string;
	
	    static createFrom(source: any = {}) {
	        return new AutomationHistory(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.execution_id = source["execution_id"];
	        this.executed_at = source["executed_at"];
	        this.status = source["status"];
	        this.duration = source["duration"];
	        this.error_message = source["error_message"];
	    }
	}
	export class AutomationSchedule {
	    cron_expression: string;
	    enabled: boolean;
	    next_run: string;
	    last_run: string;
	
	    static createFrom(source: any = {}) {
	        return new AutomationSchedule(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.cron_expression = source["cron_expression"];
	        this.enabled = source["enabled"];
	        this.next_run = source["next_run"];
	        this.last_run = source["last_run"];
	    }
	}
	export class AutomationTemplate {
	    name: string;
	    description: string;
	    task: string;
	    category: string;
	    tags: string[];
	    parameters?: Record<string, any>;
	
	    static createFrom(source: any = {}) {
	        return new AutomationTemplate(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.name = source["name"];
	        this.description = source["description"];
	        this.task = source["task"];
	        this.category = source["category"];
	        this.tags = source["tags"];
	        this.parameters = source["parameters"];
	    }
	}
	
	export class ContextBucketItem {
	    id: string;
	    type: string;
	    title: string;
	    content: string;
	    priority: string;
	    tags: string[];
	    created_at: string;
	    token_count: number;
	
	    static createFrom(source: any = {}) {
	        return new ContextBucketItem(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.id = source["id"];
	        this.type = source["type"];
	        this.title = source["title"];
	        this.content = source["content"];
	        this.priority = source["priority"];
	        this.tags = source["tags"];
	        this.created_at = source["created_at"];
	        this.token_count = source["token_count"];
	    }
	}
	export class ContextBucketSummary {
	    total_items: number;
	    total_tokens: number;
	    max_tokens: number;
	    usage_percent: number;
	
	    static createFrom(source: any = {}) {
	        return new ContextBucketSummary(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.total_items = source["total_items"];
	        this.total_tokens = source["total_tokens"];
	        this.max_tokens = source["max_tokens"];
	        this.usage_percent = source["usage_percent"];
	    }
	}
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
	export class ProviderTestResult {
	    provider: string;
	    status: string;
	    message: string;
	    latency: number;
	
	    static createFrom(source: any = {}) {
	        return new ProviderTestResult(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.provider = source["provider"];
	        this.status = source["status"];
	        this.message = source["message"];
	        this.latency = source["latency"];
	    }
	}
	export class ScheduledAutomation {
	    automation_id: string;
	    name: string;
	    schedules: AutomationSchedule[];
	    next_execution: string;
	    last_execution: string;
	
	    static createFrom(source: any = {}) {
	        return new ScheduledAutomation(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.automation_id = source["automation_id"];
	        this.name = source["name"];
	        this.schedules = this.convertValues(source["schedules"], AutomationSchedule);
	        this.next_execution = source["next_execution"];
	        this.last_execution = source["last_execution"];
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}
	export class SearchResult {
	    automations: Automation[];
	    total: number;
	
	    static createFrom(source: any = {}) {
	        return new SearchResult(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.automations = this.convertValues(source["automations"], Automation);
	        this.total = source["total"];
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}
	export class Session {
	    name: string;
	    timestamp: string;
	    message_count: number;
	    success_count: number;
	    failure_count: number;
	    conversation_history: ChatMessage[];
	
	    static createFrom(source: any = {}) {
	        return new Session(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.name = source["name"];
	        this.timestamp = source["timestamp"];
	        this.message_count = source["message_count"];
	        this.success_count = source["success_count"];
	        this.failure_count = source["failure_count"];
	        this.conversation_history = this.convertValues(source["conversation_history"], ChatMessage);
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}
	export class TaskRequest {
	    type: string;
	    message: string;
	    provider: string;
	    model: string;
	    custom_system_message?: string;
	
	    static createFrom(source: any = {}) {
	        return new TaskRequest(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.type = source["type"];
	        this.message = source["message"];
	        this.provider = source["provider"];
	        this.model = source["model"];
	        this.custom_system_message = source["custom_system_message"];
	    }
	}

}

