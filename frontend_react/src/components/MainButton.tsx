import React from "react";

type MainButtonProps = {
  children: React.ReactNode;
  onClick?: () => void;
  type?: "button" | "submit";
  disabled?: boolean;
  className?: string;
};

export default function MainButton({ children, onClick, type = "submit", disabled = false, className = "" }: MainButtonProps) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`
        flex w-full justify-center rounded-md bg-indigo-500 px-3 py-1.5 text-sm/6 font-semibold text-white
        hover:bg-indigo-400 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500
        disabled:cursor-not-allowed disabled:bg-indigo-500/40 disabled:text-white/60
        ${className}
      `}
    >
      {children}
    </button>
  );
}
