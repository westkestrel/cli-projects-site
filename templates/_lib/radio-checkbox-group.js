/**
* Copyright (c) 2026-present, Mike West
* 
* Permission is hereby granted, free of charge, to any person obtaining a copy
* of this software and associated documentation files (the "Software"), to deal
* in the Software without restriction, including without limitation the rights
* to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
* copies of the Software, and to permit persons to whom the Software is
* furnished to do so, subject to the following conditions:
* 
* The above copyright notice and this permission notice shall be included in all
* copies or substantial portions of the Software.
* 
* THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
* IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
* FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
* AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
* LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
* OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
* SOFTWARE.
* 
*/

/** (version 0.4.0)
 * Radio Checkbox Groups allow you to have checkboxes which behave like radio buttons
 * when Option-clicked or long-pressed. This is *not* a standalone script; if you include
 * it you must first include *longpress.js*.
 *
 * To use it, add `class="radio-checkbox-group"` to a container.  Now any checkboxes
 * within the container will behave normally when toggled, unless the Option key (on
 * a Mac) or Alt key (on Windows) is held, or if the checkbox is long-pressed on a
 * phone or tablet or long-clicked on computer.  Any of these gestures will trigger the
 * radio-checkbox-group behavior.
 *
 * The radio-checkbox-group behavior is very straightforward. If any checkbox other than
 * the target is checked then the target will be "soloed", which is to say that it will
 * be checked and all of the others will be unchecked. If all checkboxes other than the
 * target are unchecked then the soloing will be cancelled and all checkboxes will be
 * checked.
 *
 * Note that soloing and de-soloing will trigger **change** events for many of the
 * checkboxes in the group. If your change-handling code needs to know which checkbox
 * was actually clicked, you can check `event.target.isSoloTarget`; this will be `true`
 * for the checkbox the user clicked on and `undefined` for all the rest.
 */
 
const radioCheckboxGroupsBootstrap = () => {

const wireUpCheckboxes = (checkboxes, labels) => {
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
     *
     * As an optimization, we can bypass dispatching the event if the checkbox is already
     * in the desired state.  We must not perform this bypass if the checkbox in question
     * was the event target, though, since it will have just changed state and we *do*
     * want to dispatch the change event.
     */
    const setChecked = (checkbox, flag, eventTargetCheckbox) => {
        if (checkbox.checked == flag && checkbox !== eventTargetCheckbox) return
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
            setChecked(checkbox, target === checkbox, target)
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
     * Pseudo-event handler for long-presses on checkboxes or their labels.
     *
     * Looks to see if any other checkboxes are checked and if so, solos the target checkbox.
     * If not, de-solos the target checkbox.
     */
    const longPress = event => {
        timeout = null
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
        checkbox.addEventListener('longpress', longPress)
    }
}

const injectCSS = () => {
    cssRules = `
        .radio-checkbox-group input,
        .radio-checkbox-group label {
            /* Prevent iOS from opening the standard Copy menu when the user long-presses */
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
    const containers = document.getElementsByClassName('radio-checkbox-group')
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

radioCheckboxGroupsBootstrap()
