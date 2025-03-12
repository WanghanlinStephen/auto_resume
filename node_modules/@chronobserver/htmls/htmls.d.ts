/** Compile the given template. */
declare function compile(template: string): (data: any) => string

declare namespace compile {
    /** Compile the given HTML template. */
    export function compileHtml(template: string): (data: any) => string

    /** Compile the given XML template. */
    export function compileXml(template: string): (data: any) => string
}

export = compile
