export function Spinner({ className = "h-4 w-4" }) {
    return (<span aria-hidden="true" className={`${className} inline-block animate-spin rounded-full border-2 border-[--primary-light] border-t-[--primary]`}/>);
}
