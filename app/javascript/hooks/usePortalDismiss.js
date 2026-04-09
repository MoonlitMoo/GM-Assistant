import { useEffect } from "react"

export default function usePortalDismiss({ containerRef, enabled = true, onClose, isDismissDisabled = false }) {
  useEffect(() => {
    if (!enabled) return

    containerRef.current?.focus()
  }, [containerRef, enabled])

  useEffect(() => {
    if (!enabled) return undefined

    function handleKeyDown(event) {
      if (event.key === "Escape" && !isDismissDisabled) {
        onClose()
      }
    }

    document.addEventListener("keydown", handleKeyDown)

    return () => {
      document.removeEventListener("keydown", handleKeyDown)
    }
  }, [enabled, isDismissDisabled, onClose])
}
