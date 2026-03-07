import React from "react";

type MainButtonProps = {
  children: React.ReactNode;
  onClick?: () => void;
};

export default function MainButton({ children, onClick }: MainButtonProps) {
  return (
    <button
      onClick={onClick}
      className="flex w-full justify-center rounded-md bg-indigo-500 px-3 py-1.5 text-sm/6 font-semibold text-white hover:bg-indigo-400 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500"
    >
      {children}
    </button>
  );
}
