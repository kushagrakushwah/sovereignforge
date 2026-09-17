"use client"

import { Toaster as Sonner, type ToasterProps } from "sonner"
import { CheckCircle, Info, Warning, WarningOctagon, CircleNotch } from "@phosphor-icons/react"

const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      theme="dark"
      className="toaster group"
      icons={{
        success: <CheckCircle weight="light" className="size-4" />,
        info: <Info weight="light" className="size-4" />,
        warning: <Warning weight="light" className="size-4" />,
        error: <WarningOctagon weight="light" className="size-4 text-destructive" />,
        loading: <CircleNotch weight="light" className="size-4 animate-spin" />,
      }}
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--line-strong)",
          "--border-radius": "var(--radius)",
        } as React.CSSProperties
      }
      toastOptions={{
        classNames: {
          toast: "cn-toast font-sans text-[13px]",
          description: "text-muted-foreground!",
        },
      }}
      {...props}
    />
  )
}

export { Toaster }
