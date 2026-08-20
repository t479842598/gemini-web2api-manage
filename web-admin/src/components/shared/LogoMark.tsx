import { cn } from "@/lib/utils"

export function LogoMark({ className }: { className?: string }) {
  return (
    <img
      src="/admin/logo-icon.png"
      alt="Freebuff2API"
      className={cn("size-full object-contain", className)}
      draggable={false}
    />
  )
}
