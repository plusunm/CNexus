import { create } from "zustand";
import {
  loadFloatPanel,
  loadFloatPinned,
  loadFloatPosition,
  loadFloatStage,
  saveFloatPanel,
  saveFloatPinned,
  saveFloatPosition,
  saveFloatStage,
  type FloatPanel,
  type FloatPosition,
  type FloatStage,
} from "./floatingBarStorage";

type FloatingBarStore = {
  hydrated: boolean;
  stage: FloatStage;
  position: FloatPosition;
  activePanel: FloatPanel | null;
  pinned: boolean;
  /** Bumped when cognitive data source changes — remounts float panel content. */
  sessionEpoch: number;
  /** Dialog/menu overlay open — Tauri window expands temporarily. */
  uiModalOpen: boolean;
  hydrate: () => void;
  setStage: (stage: FloatStage) => void;
  setPosition: (pos: FloatPosition) => void;
  setActivePanel: (panel: FloatPanel | null) => void;
  togglePinned: () => void;
  setPinned: (pinned: boolean) => void;
  openPanel: (panel: FloatPanel) => void;
  collapseToBar: () => void;
  collapseToDock: () => void;
  bumpSession: () => void;
  setUiModalOpen: (open: boolean) => void;
};

export const useFloatingBarStore = create<FloatingBarStore>((set, get) => ({
  hydrated: false,
  stage: "bar",
  position: loadFloatPosition(),
  activePanel: null,
  pinned: true,
  sessionEpoch: 0,
  uiModalOpen: false,

  hydrate: () => {
    set({
      hydrated: true,
      stage: loadFloatStage(),
      position: loadFloatPosition(),
      activePanel: loadFloatPanel(),
      pinned: loadFloatPinned(),
    });
  },

  setStage: (stage) => {
    saveFloatStage(stage);
    set({ stage });
  },

  setPosition: (position) => {
    saveFloatPosition(position);
    set({ position });
  },

  setActivePanel: (activePanel) => {
    saveFloatPanel(activePanel);
    set({ activePanel });
  },

  togglePinned: () => {
    const pinned = !get().pinned;
    saveFloatPinned(pinned);
    set({ pinned });
  },

  setPinned: (pinned) => {
    saveFloatPinned(pinned);
    set({ pinned });
  },

  openPanel: (panel) => {
    saveFloatPanel(panel);
    saveFloatStage("expanded");
    set({ activePanel: panel, stage: "expanded" });
  },

  collapseToBar: () => {
    saveFloatStage("bar");
    saveFloatPanel(null);
    set({ stage: "bar", activePanel: null });
  },

  collapseToDock: () => {
    saveFloatStage("dock");
    saveFloatPanel(null);
    set({ stage: "dock", activePanel: null });
  },

  bumpSession: () => {
    set((state) => ({ sessionEpoch: state.sessionEpoch + 1 }));
  },

  setUiModalOpen: (uiModalOpen) => {
    set({ uiModalOpen });
  },
}));
