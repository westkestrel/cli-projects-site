/**
 * Collapsible Containers allow you to expand and collapse dom with the click of the mouse.
 *
 * If you decorate a container with class="collapsible-container" then its first child
 * becomes a clickable accordion control that will show or hide all of the remaining
 * elements of the section.
 *
 * ***
 *
 * This collapsible-container.js file pairs very nicely with the checkbox-radio-group.js
 * file which will allow the user to command-click (or long-press) to collapse all 
 * containers *except* the one they just selected, and with the stored-checkbox-state.js
 * file which preserves checkbox state across page-loads using local storage.
 *
 * If you do use these files you must include them *after* this file, so that this file's
 * setup will have created the checkbox html elements (and added its event listeners)
 * before those files attempt to work with them.
 */
 
const collapsibleContainerBootstrap = () => {

/**
 * Given <table><thead><tr><th>...</th></tr></thead></table>, returns the th element.
 */
const getFirstInnermostElement = element => {
    if (!element.firstElementChild) return element
    return getFirstInnermostElement(element.firstElementChild)
}

const setCollapsed = (section, flag) => {
    const classNames = section.getAttribute('class').split(/ +/).filter(s => s != 'collapsed' && s != 'expanded')
    if (flag) classNames.push('collapsed')
    else classNames.push('expanded')
    section.setAttribute('class', classNames.join(' '))
}

const makeOnChangeHandler = section => {
    return event => {
        setCollapsed(section, !event.target.checked)
    }
}

const wireUpCollapsibles = () => {
    const collapsibles = document.getElementsByClassName('collapsible-container')
    for (section of collapsibles) {
        const innermost = getFirstInnermostElement(section)
        const id = 's-' + innermost.innerHTML.toLocaleLowerCase().replace(/\W/g, '-')
        const input = document.createElement('input')
        input.setAttribute('type', 'checkbox')
        input.setAttribute('id', id)
        input.checked = true
        const label = document.createElement('label')
        label.setAttribute('for', id)
        label.innerHTML = innermost.innerHTML
        innermost.innerHTML = ''
        innermost.appendChild(input)
        innermost.appendChild(label)
        input.addEventListener('change', makeOnChangeHandler(section))
    }
    cssRules = `
        .collapsible-container.collapsed > :first-child {
            color: gray;
        }
        .collapsible-container:not(.collapsed) > :first-child:hover,
        .collapsible-container.collapsed > :first-child:not(:hover) {
            text-decoration: line-through;
        }
        .collapsible-container.collapsed > :not(:first-child) {
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

collapsibleContainerBootstrap()
