import type {ButtonHTMLAttributes, ReactNode} from "react";

type SecondaryButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
    children: ReactNode;
};

export default function SecondaryButton({
    children,
    className = "",
    type = "button",
    ...buttonProps
}: SecondaryButtonProps) {
    return (
        <button
            type={type}
            className={`
                rounded-md border border-cyan-300/25 bg-cyan-300/10 px-3 py-1.5 text-sm/6 font-semibold text-cyan-50 transition
                hover:bg-cyan-300/20 disabled:cursor-not-allowed disabled:border-cyan-300/10 disabled:bg-cyan-300/5 disabled:text-cyan-100/50
                ${className}
            `}
            {...buttonProps}
        >
            {children}
        </button>
    );
}
