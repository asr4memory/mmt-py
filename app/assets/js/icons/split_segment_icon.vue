<template>
    <!-- Outline style: no fill, currentColor stroke at 1.7 width. The two
    solid horizontal lines are the outer boundaries of the segment, the dashed
    line between them is the boundary the split introduces, and the two arrows
    are the halves moving apart. -->
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"
        stroke-linecap="round" stroke-linejoin="round">
        <line x1="4" y1="4" x2="20" y2="4" />
        <line x1="4" y1="20" x2="20" y2="20" />
        <line x1="4" y1="12" x2="20" y2="12" stroke-dasharray="3 3" />
        <polyline points="9.5,8 12,5.5 14.5,8" />
        <polyline points="9.5,16 12,18.5 14.5,16" />
    </svg>
</template>
