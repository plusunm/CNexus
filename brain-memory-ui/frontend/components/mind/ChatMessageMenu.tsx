"use client";

import { FloatingAppMenu, type FloatingMenuItem } from "./floating/FloatingAppMenu";

type Props = {
  position: { x: number; y: number };
  onCopy: () => void;
  onShare: () => void;
  onClose: () => void;
};

export function ChatMessageMenu({ position, onCopy, onShare, onClose }: Props) {
  const items: FloatingMenuItem[] = [
    { id: "copy", label: "复制内容", onClick: onCopy },
    { id: "share", label: "分享对话", onClick: onShare },
  ];

  return <FloatingAppMenu items={items} position={position} placement="portal" onClose={onClose} />;
}
