let currentGameId = null;
let scale = 1;
let isPanning = false;
let startPos = { x: 0, y: 0 };
let transform = { x: 0, y: 0 };
let currentStoryMap = null; // Variable to hold the latest story map data

// --- Main Event Listener ---
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Mermaid once on page load
    // The theme is configured in setupThemeToggle to match the page theme.
    mermaid.initialize({
        startOnLoad: false,
    });

    document.getElementById('new-game-btn')?.addEventListener('click', resetGame);
    setupZoomAndPan();
    setupThemeToggle();
    checkForActiveGame();
});

// --- Game State Management ---

async function checkForActiveGame() {
    const activeGameId = localStorage.getItem('activeGameId');
    if (activeGameId) {
        await resumeGame(activeGameId);
    }
}

async function resumeGame(gameId) {
    try {
        // The new GET endpoint returns the full game state
        const response = await fetch(`/api/v1/game/${gameId}`);
        if (!response.ok) {
            if (response.status === 404) {
                localStorage.removeItem('activeGameId');
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        currentGameId = gameId;
        updateFullUI(data);
        showGameWrapper();

    } catch (error) {
        console.error("Failed to resume game:", error);
        localStorage.removeItem('activeGameId'); // Clear broken ID
        resetGame(); // Go back to the main menu
    }
}

async function startGame(storyType) {
    const selectionDiv = document.getElementById('story-type-selection');
    selectionDiv.innerHTML = `<div class="text-center"><p class="text-xl">正在为您生成专属故事，请稍候...</p><div class="loader mt-4"></div></div>`;

    try {
        const response = await fetch('/api/v1/game', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ story_type: storyType }),
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const data = await response.json();
        currentGameId = data.game_id;
        localStorage.setItem('activeGameId', currentGameId);

        updateFullUI(data);
        showGameWrapper();

    } catch (error) {
        console.error("Error starting game:", error);
        selectionDiv.innerHTML = `<p class="text-red-500">游戏启动失败，请刷新页面重试。</p>`;
    }
}

async function resetGame() {
    const gameId = localStorage.getItem('activeGameId');
    if (gameId) {
        try {
            // No need to wait for this to complete
            fetch(`/api/v1/game/${gameId}`, { method: 'DELETE' });
        } catch (error) {
            console.error("Failed to delete game on server:", error);
        }
    }
    
    localStorage.removeItem('activeGameId');
    currentGameId = null;
    
    // Instead of trying to manually reset the state, which is complex,
    // simply reload the page. This is the most robust way to ensure
    // a clean start for a new game.
    location.reload();
}

async function makeChoice(choiceText) {
    if (!currentGameId) return;

    const choicesContainer = document.getElementById('choices-container');
    const buttons = choicesContainer.querySelectorAll('button');
    
    // Disable all buttons and show loading state
    buttons.forEach(button => {
        button.disabled = true;
        button.classList.add('opacity-50', 'cursor-not-allowed');
        if (button.textContent === choiceText) {
            button.innerHTML = `<span>加载中...</span>`;
        }
    });

    try {
        const response = await fetch(`/api/v1/game/${currentGameId}/choice`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ choice_text: choiceText }),
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const data = await response.json();
        updateFullUI(data);


    } catch (error) {
        console.error("Error making choice:", error);
        // Re-enable buttons on error
        buttons.forEach(button => {
            button.disabled = false;
            button.classList.remove('opacity-50', 'cursor-not-allowed');
            if (button.textContent === '加载中...') {
                button.textContent = choiceText;
            }
        });
    }
}

// --- UI Update Functions ---

function showGameWrapper() {
    document.getElementById('story-type-selection').classList.add('hidden');
    const wrapper = document.getElementById('game-wrapper');
    wrapper.classList.remove('hidden');
    wrapper.classList.add('flex');
}

function updateFullUI(data) {
    document.getElementById('story-title').textContent = data.title;
    if(data.story_map) {
        currentStoryMap = data.story_map; // Store the map data
        renderStoryMap(currentStoryMap, data.scene.current_node_id);
    }
    
    updateHistory(data.story_history);
    // Pass the full scene object to updateScene
    updateScene(data.scene);
}

function updateScene(scene) {
    const storyContent = document.getElementById('story-content');
    const scrollContainer = storyContent.parentElement;
    const choicesContainer = document.getElementById('choices-container');

    storyContent.textContent = scene.content;
    // Store the current node ID on the element for later access (e.g., theme switching)
    if (scene.current_node_id) {
        storyContent.dataset.currentNodeId = scene.current_node_id;
    }
    choicesContainer.innerHTML = '';

    if (scene.choices && scene.choices.length > 0) {
        scene.choices.forEach(choice => {
            const button = document.createElement('button');
            button.textContent = choice.text;
            // We now send the text content directly
            button.onclick = () => makeChoice(choice.text);
            button.className = 'bg-accent hover:bg-accent-hover text-white font-bold py-2 px-4 rounded transition duration-300 w-full';
            choicesContainer.appendChild(button);
        });
    } else {
        choicesContainer.innerHTML = '<p class="text-center text-gray-400">故事似乎已经走到了尽头。</p>';
    }

    // 确保新内容从第一行显示，延迟执行确保内容渲染完成
    if (storyContent) {
        requestAnimationFrame(() => {
            scrollContainer.scrollTop = 0;
        });
    }
}

function updateHistory(storyHistory) {
    const historyLog = document.getElementById('history-log');
    historyLog.innerHTML = '';

    // The last item is the current scene, which is not part of the history log.
    const historyToShow = storyHistory.slice(0, -1);
    if (historyToShow.length === 0) return;

    // This new logic correctly handles the display by iterating through the history
    // and creating the appropriate element for each item based on its role.
    historyToShow.forEach(item => {
        const turnContainer = document.createElement('div');
        turnContainer.className = 'mb-4';

        if (item.role === 'assistant') {
            const sceneElement = document.createElement('div');
            sceneElement.className = 'p-3 bg-background-secondary rounded-lg';
            sceneElement.textContent = item.content;
            turnContainer.appendChild(sceneElement);
        } else if (item.role === 'user') {
            const choiceElement = document.createElement('div');
            // We'll wrap the scene and choice in a container for better grouping
            // but the choice itself is what's styled differently.
            choiceElement.className = 'p-2 text-accent italic text-left';
            choiceElement.textContent = `> ${item.content}`;
            turnContainer.appendChild(choiceElement);
        }
        
        historyLog.appendChild(turnContainer);
    });
    
    historyLog.scrollTop = historyLog.scrollHeight;
}

function renderStoryMap(storyMap, currentNodeId) {
    if (!storyMap || !storyMap.nodes) {
        console.error("Invalid story map data provided.");
        return;
    }

    scale = 1;
    transform = { x: 0, y: 0 };
    const panTarget = document.getElementById('zoom-pan-container');
    if(panTarget) {
        panTarget.style.transform = 'translate(0px, 0px) scale(1)';
    }

    const { nodes, edges } = storyMap;
    let graphDefinition = 'graph TD;\n';

    nodes.forEach(node => {
        const label = node.label.replace(/"/g, '"');
        graphDefinition += `    ${node.id}["${label}"];\n`;
    });

    // Edges might not exist in the new format, handle gracefully
    if (edges) {
        edges.forEach(edge => {
            const label = edge.label.replace(/"/g, '"');
            graphDefinition += `    ${edge.from} -- "${label}" --> ${edge.to};\n`;
        });
    }

    const container = document.querySelector("#zoom-pan-container .mermaid");
    container.textContent = graphDefinition;
    container.removeAttribute('data-processed');
    
    // Simple run command. All styling is now handled by external CSS.
    mermaid.run({
        nodes: [container]
    }).then(() => {
        // On mobile devices, do not focus on the current node to avoid offset issues
        const isMobile = /Mobi|Android/i.test(navigator.userAgent);
        if (isMobile) {
            focusOnNode();
        } else {
            focusOnNode(currentNodeId);
        }
    }).catch(err => {
        console.error("Mermaid rendering failed:", err);
    });
}

// --- Zoom and Pan Functionality ---

function updateTransform() {
    const panTarget = document.getElementById('zoom-pan-container');
    if (panTarget) {
        panTarget.style.transform = `translate(${transform.x}px, ${transform.y}px) scale(${scale})`;
    }
}

function focusOnNode(nodeId) {
    const container = document.getElementById('story-map-container');
    const panTarget = document.getElementById('zoom-pan-container');
    const svg = panTarget ? panTarget.querySelector('svg') : null;

    if (!container || !panTarget) return;

    // If the SVG isn't rendered yet, retry shortly.
    if (!svg) {
        setTimeout(() => focusOnNode(nodeId), 100);
        return;
    }

    // Use getBoundingClientRect for more accurate size on mobile devices
    const containerRect = container.getBoundingClientRect();
    const containerWidth = containerRect.width;
    const containerHeight = containerRect.height;

    // If a specific node ID is provided, focus on it.
    if (nodeId) {
        // Mermaid uses the node ID for the DOM element's ID
        const nodeElement = svg.querySelector(`[data-id="${nodeId}"]`);
        if (nodeElement) {
            const transformAttr = nodeElement.getAttribute('transform');
            const match = transformAttr ? /translate\(\s*([0-9.-]+)\s*,\s*([0-9.-]+)\s*\)/.exec(transformAttr) : null;

            if (match) {
                const nodeCenterX = parseFloat(match[1]);
                const nodeCenterY = parseFloat(match[2]);

                // --- Optimized Positioning Logic ---
                // Horizontally, we center the node.
                transform.x = (containerWidth / 2) - (nodeCenterX * scale);

                // Vertically, we position the node near the center (50% from the top)
                // to better center the node on both mobile and desktop.
                transform.y = (containerHeight * 0.5) - (nodeCenterY * scale);

                updateTransform();
                return; // Exit after successfully focusing on the node
            } else {
                console.warn(`Could not parse transform for node '${nodeId}'. Centering map instead.`);
            }
        } else {
            console.warn(`Node with ID '${nodeId}' not found in the story map. Centering map instead.`);
        }
    }

    // Fallback: If no nodeId is provided or the node is not found, center the entire map.
    const svgRect = svg.getBBox();
    const svgWidth = svgRect.width * scale;
    const svgHeight = svgRect.height * scale;

    transform.x = (containerWidth > svgWidth) ? (containerWidth - svgWidth) / 2 : 0;
    transform.y = (containerHeight > svgHeight) ? (containerHeight - svgHeight) / 2 : 0;
    
    updateTransform();
}

function setupZoomAndPan() {
    const zoomInBtn = document.getElementById('zoom-in-btn');
    const zoomOutBtn = document.getElementById('zoom-out-btn');
    const zoomResetBtn = document.getElementById('zoom-reset-btn');
    const container = document.getElementById('story-map-container');

    if (!zoomInBtn || !zoomOutBtn || !zoomResetBtn || !container) {
        console.error("Zoom controls or container not found.");
        return;
    }

    // --- Button Events ---
    zoomInBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        scale = Math.min(3, scale + 0.2);
        updateTransform();
    });

    zoomOutBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        scale = Math.max(0.2, scale - 0.2);
        updateTransform();
    });

    zoomResetBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        scale = 1;
        // Reset zoom and center the map (or focus on the start node if available)
        focusOnNode();
    });

    // --- Mouse Pan Events ---
    container.addEventListener('mousedown', (e) => {
        if (e.button !== 0) return; // Only main mouse button
        isPanning = true;
        container.classList.add('grabbing');
        startPos = { x: e.clientX - transform.x, y: e.clientY - transform.y };
        e.preventDefault();
    });

    container.addEventListener('mousemove', (e) => {
        if (!isPanning) return;
        transform.x = e.clientX - startPos.x;
        transform.y = e.clientY - startPos.y;
        updateTransform();
    });

    const endPan = () => {
        isPanning = false;
        container.classList.remove('grabbing');
    };
    container.addEventListener('mouseup', endPan);
    container.addEventListener('mouseleave', endPan);

    // --- Wheel Zoom Event ---
    container.addEventListener('wheel', (e) => {
        e.preventDefault();
        const rect = container.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        // Adjust scale factor for smoother zooming
        const scaleFactor = 1 - e.deltaY * 0.001;
        const newScale = Math.max(0.2, Math.min(3, scale * scaleFactor));

        // Adjust transform to zoom towards the mouse position
        transform.x = mouseX - (mouseX - transform.x) * (newScale / scale);
        transform.y = mouseY - (mouseY - transform.y) * (newScale / scale);
        
        scale = newScale;
        updateTransform();
    }, { passive: false });

    // --- Touch Pan & Pinch Events ---
    let initialPinchDistance = 0;

    container.addEventListener('touchstart', (e) => {
        // Prevent default browser actions like scrolling or zooming
        if (e.touches.length > 0) {
            e.preventDefault();
        }

        if (e.touches.length === 1) {
            isPanning = true;
            container.classList.add('grabbing');
            const touch = e.touches[0];
            startPos = { x: touch.clientX - transform.x, y: touch.clientY - transform.y };
        } else if (e.touches.length === 2) {
            isPanning = false; // Stop panning if two fingers are used
            const touch1 = e.touches[0];
            const touch2 = e.touches[1];
            initialPinchDistance = Math.hypot(touch1.clientX - touch2.clientX, touch1.clientY - touch2.clientY);
        }
    }, { passive: false });

    container.addEventListener('touchmove', (e) => {
        if (e.touches.length > 0) {
            e.preventDefault();
        }

        if (e.touches.length === 1 && isPanning) {
            const touch = e.touches[0];
            transform.x = touch.clientX - startPos.x;
            transform.y = touch.clientY - startPos.y;
            updateTransform();
        } else if (e.touches.length === 2 && initialPinchDistance > 0) {
            const touch1 = e.touches[0];
            const touch2 = e.touches[1];
            const currentPinchDistance = Math.hypot(touch1.clientX - touch2.clientX, touch1.clientY - touch2.clientY);
            const scaleFactor = currentPinchDistance / initialPinchDistance;
            
            const newScale = Math.max(0.2, Math.min(3, scale * scaleFactor));

            // Focal point is the midpoint between the two touches
            const rect = container.getBoundingClientRect();
            const midX = ((touch1.clientX + touch2.clientX) / 2) - rect.left;
            const midY = ((touch1.clientY + touch2.clientY) / 2) - rect.top;

            // Adjust transform to zoom towards the pinch center
            transform.x = midX - (midX - transform.x) * (newScale / scale);
            transform.y = midY - (midY - transform.y) * (newScale / scale);
            
            scale = newScale;
            // Update initial distance for smooth scaling in the same gesture
            initialPinchDistance = currentPinchDistance;
            updateTransform();
        }
    }, { passive: false });

    container.addEventListener('touchend', (e) => {
        if (e.touches.length < 2) {
            isPanning = false;
            container.classList.remove('grabbing');
            initialPinchDistance = 0;
        }
    });
    // --- Window Resize Listener ---
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            const storyContent = document.getElementById('story-content');
            if (storyContent && storyContent.dataset.currentNodeId) {
                focusOnNode(storyContent.dataset.currentNodeId);
            }
        }, 250); // 250ms debounce
    });
}

// --- Theme Toggle ---
function setupThemeToggle() {
    const themeToggleBtn = document.getElementById('theme-toggle');
    const themeToggleDarkIcon = document.getElementById('theme-toggle-dark-icon');
    const themeToggleLightIcon = document.getElementById('theme-toggle-light-icon');

    // Function to apply theme
    const applyTheme = (theme) => {
        const isDark = theme === 'dark';
        
        // 1. Update HTML class
        document.documentElement.classList.toggle('dark', isDark);

        // 2. Update toggle icon
        themeToggleLightIcon.classList.toggle('hidden', !isDark);
        themeToggleDarkIcon.classList.toggle('hidden', isDark);
        
        // 3. Save preference
        localStorage.setItem('theme', theme);

        // 4. Update Mermaid's theme to match. It's safe to call initialize again.
        mermaid.initialize({ theme: theme });

        // 5. Re-render Mermaid diagram by calling the main render function
        if (currentStoryMap) {
            // Pass the current node ID if available, otherwise it will just center
            const currentSceneNode = document.getElementById('story-content').dataset.currentNodeId;
            renderStoryMap(currentStoryMap, currentSceneNode);
        }
    };

    // Check for saved theme in local storage or user's system preference
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    // Set initial theme
    applyTheme(savedTheme || (prefersDark ? 'dark' : 'light'));

    // Add event listener for the button
    themeToggleBtn.addEventListener('click', () => {
        const isCurrentlyDark = document.documentElement.classList.contains('dark');
        applyTheme(isCurrentlyDark ? 'light' : 'dark');
    });

    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
        // Only change if no theme is manually set in local storage
        // Only change if no theme is manually set in local storage
        if (!localStorage.getItem('theme')) {
            applyTheme(e.matches ? 'dark' : 'light');
        }
    });
}
