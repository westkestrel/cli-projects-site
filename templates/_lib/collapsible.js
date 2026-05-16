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
 * Collapsible allows you to expand and collapse sections with the click of the mouse.
 *
 * To use it, you have a give a container (typically a DIV, SECTION, or TABLE) the class
 * "collapsible-section".  The first child of the container (typically a H2 or TR) will
 * be turned into a trigger that, when clicked, causes the remaining children to appear
 * or disappear.
 *
 * Note that the first element child does not *have* to include a button, but it is good
 * practice for it to do so as this helps with the accessibility of your web page.
 *
 * e.g.,
 * ```html
 * <section class="collapsible-section">
 *   <h2><button>Rutabagas</button></h2>
 *   <p>Rutabagas are a vegetable.</p>
 *   <p>Some people like them. Some people don't</p>
 * </section>
 * ```
 *
 * If you also include the *longpress.js* script then the user can long-press or
 * Option-click (Alt-click on Windows) a button to expand the section and collapse
 * all others.  You must include the *longpress.js* script before *collapsible.js*.
 */
 
const collapsibleBootstrap = () => {

const getLocalStorageKey = (element) => {
    if (!element) return 'collapse-NULL'
    return'collapse-' + element.innerHTML.replace(/<.*?>/g, '').replace(/\W+/g, '-')
}

const isCollapsed = (elementOrClassString) => {
    classNames = elementOrClassString.getAttribute
        ? elementOrClassString.getAttribute('class')
        : elementOrClassString
    return (classNames || '').split(' ').some(s => s == 'collapsed')
}

const toggle = (event, solo) => {
    if (event.target.justHadLongPress) {
        event.preventDefault()
        return true
    }
    
    var targetContainer = event.target
    var className = null
    while (targetContainer) {
        className = targetContainer.getAttribute('class') || ''
        if (className.indexOf('collapsible-section') != -1) break;
        targetContainer = targetContainer.parentNode
    }
    if (!targetContainer) {
        console.error('no collapsible-section found!')
        return
    }
    const containers = solo
    ? Array.from(document.getElementsByClassName('collapsible-section'))
    : [targetContainer]
    
    // if we are soloing, we always expand the target.  If not, we toggle
    const shouldCollapseTarget = solo
    ? false
    : !isCollapsed(className)
    
    // if we are soloing, we collapse the others unless they were all already collapsed
    // if we are not soloing this flag is irrelevant since we won't process any other elements
    const shouldCollapseOthers = containers.some(e => e !== targetContainer && !isCollapsed(e))

    for (container of containers) {
        const shouldCollapse = container === targetContainer ? shouldCollapseTarget : shouldCollapseOthers
        window.localStorage.setItem(getLocalStorageKey(container.firstElementChild), shouldCollapse)
        const classNames = container.getAttribute('class').split(' ').filter(s => s != 'collapsed')
        if (shouldCollapse) {
            classNames.push('collapsed')
        }
        container.setAttribute('class', classNames.join(' '))
    }
}

const longPress = (event) => {
    toggle(event, true)
}

const wireUpCollapsibles = () => {
    const collapsibles = document.getElementsByClassName('collapsible-section')
    for (section of collapsibles) {
        const key = getLocalStorageKey(section.firstElementChild)
        const first = section.firstElementChild
        const target = first.getElementsByTagName('button')[0] || first
        target.addEventListener('click', toggle)
        target.addEventListener('longpress', longPress)
        if (window.localStorage.getItem(key) == 'true') {
            section.setAttribute('class', section.getAttribute('class') + ' collapsed')
        }
    }
    cssRules = `
        .collapsible-section > :first-child button,
        .collapsible-section > :first-child input,
        .collapsible-section > :first-child label {
            /* Prevent iOS from opening the standard Copy menu when the user long-presses */
            -webkit-touch-callout: none !important;
            -webkit-user-select: none !important;
        }
        .collapsible-section.collapsed > :not(:first-child) {
            display: none;
        }
    `.replace(/\n {4,8}/g, '\n')
    const head = document.getElementsByTagName('head')[0]
    const style = document.createElement('style')
    style.setAttribute('type', 'text/css')
    style.innerHTML = cssRules
    head.appendChild(style)
}

window.addEventListener('load', wireUpCollapsibles)

}

collapsibleBootstrap()
