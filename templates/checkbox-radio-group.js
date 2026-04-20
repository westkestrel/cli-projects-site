/**
 * Checkbox Radio Groups allows you to have checkboxes which behave like radio buttons
 * when Command-clicked or long-pressed.
 *
 * To use it, add the class 'checkbox-radio-group' to a container.  Now any checkboxes
 * within the container will behave normally when toggled, unless the Command key (on
 * a mac) or Control key (on Windows) is held, or if the checkbox is long-pressed on a
 * phone or tablet or long-clicked on computer.  Any of these gestures will trigger the
 * checkbox-radio-group behavior.
 *
 * The checkbox-radio-group behavior is very straightforward. If any checkbox other than
 * the target is checked then the target will be "soloed", which is to say that it will
 * be checked and all of the others will be unchecked. If all checkboxes other than the
 * target are unchecked then the soloing will be cancelled and all checkboxes will be
 * checked.
 *
 * Note that soloing and de-soloing will trigger 'change' events for many of the
 * checkboxes in the group. If your change-handling code needs to know which checkbox
 * was actually clicked, you can check event.target.isSoloTarget; this will be true for
 * the checkbox the user clicked on and undefined for all the rest.
 */
 
const radioCheckboxesBootstrap = () => {

const wireUpCheckboxes = (checkboxes, labels) => {
    var metaKey = false
    var justPerformedLongPress = false
    var timeout = null
    
    /**
     * Returns the id of the checkbox associated with the given element node.  This will be
     * - the value of the 'id' attribute, if the element is a checkbox
     * - the value of the 'for' attribute, if the element is a label
     * - the 'id' or 'for' of the parent element, if neither of the above apply
     */
    const getCheckboxId = element => {
        if (!element) return null
        const type = element.tagName
        const id = type == 'LABEL'
            ? element.getAttribute('for')
            : type == 'INPUT' ? element.getAttribute('id') : null
        if (id) return id
        return getCheckboxId(element.parentNode)
    }
    
    /**
     * Returns the checkbox associated with the given element, which may be
     * - a checkbox
     * - a label with a 'for' attribute
     * - a child of such a label
     *
     * Returns null if no such checkbox can be found.
     */
    const getAssociatedCheckbox = element => {
        if (!element) return null;
        if (element.tagName === 'INPUT' && element.getAttribute('type') === 'checkbox') return element;
        const id = getCheckboxId(element)
        return id && document.getElementById(id)
    }
    
    /**
     * Returns true iff any checkbox other than the given target is currently checked.
     */
    const isAnyOtherCheckboxChecked = target => {
        for (checkbox of checkboxes) {
            if (checkbox === target) continue
            if (checkbox.checked) return true
        }
        return false
    }
    
    /**
     * Sets the state of the checkbox and dispatches a change event.
     */
    const setChecked = (checkbox, flag) => {
        if (checkbox.checked == flag) return
        checkbox.checked = flag
        const event = new Event('change')
        event.target = checkbox
        checkbox.dispatchEvent(event)
    }
    
    /**
     * Checks the target checkbox and unchecks all the others.
     */
    const solo = target => {
        for (checkbox of checkboxes) {
            setChecked(checkbox, target === checkbox)
        }
    }
    
    /**
     * Checks all checkboxes.
     */
    const desolo = target => {
        for (checkbox of checkboxes) {
            setChecked(checkbox, true)
        }
    }
    
    /**
     * Event handler for mousedown or touchstart events on either checkboxes or their labels.
     *
     * Clears any outstanding long-press timers and starts a new one.
     */
    const hit = event => {
        metaKey = event.metaKey
        justPerformedLongPress = false
        if (timeout) clearTimeout(timeout)
        timeout = setTimeout(longPress, 1000, event)
        return false
    }
    
    /**
     * Event handler for mouseup or touchend events on either checkboxes or their labels.
     *
     * Clears any outstanding long-press timers to prevent the long-press action from occurring.
     */
    const release = event => {
        metaKey = event.metaKey
        if (timeout) {
            clearTimeout(timeout)
            timeout = null
        }
        
        // command-clicking is the same as a long-press
        if (event.metaKey && !justPerformedLongPress) {
            longPress(event)
        }
        
        // This gets a bit tricky... If the user long-pressed on a checkbox then we will
        // have soloed (or de-soloed) the checkboxes when the long-press timer went off.
        // But then the user releases the mouse button or lifts their finger and the
        // built-in checkbox toggling occurs and deselects the target.
        // We want to prevent this so the target remains selected, but it appears that
        // event.preventDefault() on the mouseup event does not prevent the change event
        // from occurring... so we need to take a different approach.
        if (justPerformedLongPress) {
            const checkbox = getAssociatedCheckbox(event.target)
            const wasChecked = checkbox.checked
            
            // On macOS we can simply toggle the checkbox manually (to un-checked) and then
            // when the built-in checkbox-toggling code executes it will be set to checked
            // and the event handlers will fire. That second firing is unnecessary, but
            // harmless since the checkbox state is correct.
            if (checkbox) {
                checkbox.checked = !wasChecked
            } else {
                console.error('Could not find a checkbox associated with event', event)
            }
            
            // Unfortunately, the above pre-toggling does NOT work on iOS, so instead
            // we need to wait until the change event has propagated and then change it
            // back. This is unfortunate because any logic associated with toggling the
            // checkbox will fire twice (once with checked==false and then again with
            // checked=true), but it seems to happen before the screen redraws so there
            // is no visible flicker.
            setTimeout(() => {
                if (checkbox.checked != wasChecked) {
                    checkbox.checked = wasChecked;
                    const event = new Event('change')
                    event.target = checkbox
                    checkbox.dispatchEvent(event)
                }
            }, 0)
        }
        return false
    }
    
    /**
     * Pseudo-event handler for long-presses on checkboxes or their labels.
     *
     * Looks to see if any other checkboxes are checked and if so, solos the target checkbox.
     * If not, de-solos the target checkbox.
     */
    const longPress = event => {
        timeout = null
        metaKey = true
        const htmlFor = getCheckboxId(event.target)
        const checkbox = htmlFor ? document.getElementById(htmlFor) : event.target
        if (!checkbox) {
            console.error('no checkbox is associated with the event', event)
            return false
        }
        checkbox.isSoloTarget = true
        if (isAnyOtherCheckboxChecked(checkbox)) {
            solo(checkbox)
        } else {
            desolo(checkbox)
        }
        justPerformedLongPress = true
        setTimeout(() => delete checkbox.isSoloTarget, 100)
        
        return false
    }
    
    for (checkbox of checkboxes) {
        checkbox.addEventListener('mousedown', hit)
        checkbox.addEventListener('mouseup', release)
        checkbox.addEventListener('touchstart', hit)
        checkbox.addEventListener('touchend', release)
    }
    for (label of labels) {
        label.addEventListener('mousedown', hit)
        label.addEventListener('mouseup', release)
        label.addEventListener('touchstart', hit)
        label.addEventListener('touchend', release)
    }
}

const injectCSS = () => {
    cssRules = `
        .checkbox-radio-group input,
        .checkbox-radio-group label {
            -webkit-touch-callout: none !important;
            -webkit-user-select: none !important;
        }
    `.replace(/\n {4,8}/g, '\n')
    const head = document.getElementsByTagName('head')[0]
    const style = document.createElement('style')
    style.setAttribute('type', 'text/css')
    style.innerHTML = cssRules
    head.appendChild(style)
}

const wireUpRadioGroups = () => {
    const containers = document.getElementsByClassName('checkbox-radio-group')
    for (container of containers) {
        const checkboxes = Array.from(container.getElementsByTagName('input'))
            .filter(e => e.getAttribute('type') == 'checkbox')
        const checkboxIds = new Set(checkboxes.map(e => e.getAttribute('id')).filter(id => !!id))
        const labels = Array.from(container.getElementsByTagName('label'))
            .filter(e => checkboxIds.has(e.getAttribute('for')))
        wireUpCheckboxes(checkboxes, labels)
    }
    injectCSS()
}

window.addEventListener('load', wireUpRadioGroups)

}

radioCheckboxesBootstrap()
