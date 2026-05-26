"use client";

import { Toaster as Sonner } from "sonner";

type ToasterProps = React.ComponentProps<typeof Sonner>;

function Toaster({ ...props }: ToasterProps) {
  return <Sonner theme="light" className="toaster group" {...props} />;
}

export { Toaster };
